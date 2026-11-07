// Native pgx version from Harbor a97e7b835d1364e2cc11fd706a15171a5c9d5d77/src/go.mod.
// Exercises real pgx configuration and Go TLS over an in-memory pipe. No DB,
// Harbor binary, network listener, image or user certificate is used.
package harborpgx

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
)

const host = "harbor-postgres-rw.harbor.svc.cluster.local"

func certificates(t *testing.T, directory string) tls.Certificate {
	t.Helper()
	var server tls.Certificate
	for _, name := range []string{"ca", "other"} {
		pub, key, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			t.Fatal(err)
		}
		root := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: name},
			NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour),
			IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign}
		der, err := x509.CreateCertificate(rand.Reader, root, root, pub, key)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(directory, name+".crt"), pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0600); err != nil {
			t.Fatal(err)
		}
		if name != "ca" {
			continue
		}
		leafPub, leafKey, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			t.Fatal(err)
		}
		leaf := &x509.Certificate{SerialNumber: big.NewInt(2), DNSNames: []string{host},
			NotBefore: root.NotBefore, NotAfter: root.NotAfter, KeyUsage: x509.KeyUsageDigitalSignature,
			ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
		leafDER, err := x509.CreateCertificate(rand.Reader, leaf, root, leafPub, key)
		if err != nil {
			t.Fatal(err)
		}
		server = tls.Certificate{Certificate: [][]byte{leafDER}, PrivateKey: leafKey}
	}
	return server
}

func TestHarborPGXTrust(t *testing.T) {
	directory := t.TempDir()
	serverCertificate := certificates(t, directory)
	// The connection string matches Harbor's DAO form and must override an
	// insecure environment. Do not inherit optional runner connection settings.
	for _, entry := range os.Environ() {
		key := strings.SplitN(entry, "=", 2)[0]
		if strings.HasPrefix(key, "PG") {
			t.Setenv(key, "")
		}
	}
	t.Setenv("HOME", directory)
	t.Setenv("PGSSLMODE", "disable")
	for _, scenario := range []struct {
		name, root, hostname string
		valid                bool
	}{
		{"mounted-root", "ca.crt", host, true},
		{"wrong-root", "other.crt", host, false},
		{"wrong-hostname", "ca.crt", "other.invalid", false},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			t.Setenv("PGSSLROOTCERT", filepath.Join(directory, scenario.root))
			config, err := pgconn.ParseConfig("host=" + scenario.hostname + " port=5432 user=fixture password=fixture dbname=harbor sslmode=verify-full timezone=UTC")
			if err != nil {
				t.Fatal(err)
			}
			if config.TLSConfig == nil || config.TLSConfig.InsecureSkipVerify || config.TLSConfig.ServerName != scenario.hostname || config.TLSConfig.RootCAs == nil {
				t.Fatal("verify-full and explicit roots must reach native TLS")
			}
			for _, fallback := range config.Fallbacks {
				if fallback.TLSConfig == nil || fallback.TLSConfig.InsecureSkipVerify {
					t.Fatal("plaintext or unverified fallback")
				}
			}
			client, server := net.Pipe()
			defer client.Close()
			defer server.Close()
			client.SetDeadline(time.Now().Add(3 * time.Second))
			server.SetDeadline(time.Now().Add(3 * time.Second))
			done := make(chan error, 1)
			go func() {
				done <- tls.Server(server, &tls.Config{Certificates: []tls.Certificate{serverCertificate}}).Handshake()
			}()
			err = tls.Client(client, config.TLSConfig).Handshake()
			client.Close()
			server.Close()
			serverErr := <-done
			if scenario.valid && (err != nil || serverErr != nil) {
				t.Fatalf("matching CA and hostname failed: %v / %v", err, serverErr)
			}
			if !scenario.valid && err == nil {
				t.Fatal("wrong CA or hostname accepted")
			}
		})
	}
	for _, file := range []string{"missing.crt", "invalid.crt"} {
		t.Run(file, func(t *testing.T) {
			if file == "invalid.crt" {
				if err := os.WriteFile(filepath.Join(directory, file), []byte("not a certificate"), 0600); err != nil {
					t.Fatal(err)
				}
			}
			t.Setenv("PGSSLROOTCERT", filepath.Join(directory, file))
			_, err := pgconn.ParseConfig("host=" + host + " sslmode=verify-full")
			if err == nil || !strings.Contains(err.Error(), "CA") {
				t.Fatalf("invalid explicit root did not fail closed: %v", err)
			}
		})
	}
}
