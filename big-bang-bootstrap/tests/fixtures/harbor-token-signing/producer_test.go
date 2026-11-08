package signing_test

import (
	"bytes"
	"crypto/x509"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"

	"github.com/docker/libtrust"
)

// Only the synthetic real-Ansible fixture supplies this temporary bundle path.
// Default discovery never reads any operator input, kubeconfig or real key.
func TestGeneratedTokenBundle(t *testing.T) {
	bundle := os.Getenv("HARBOR_SYNTHETIC_TOKEN_BUNDLE")
	if bundle == "" {
		return
	}
	keyPEM, err := os.ReadFile(filepath.Join(bundle, "delivery", "token-signing", "tls.key"))
	if err != nil {
		t.Fatal(err)
	}
	key, err := libtrust.UnmarshalPrivateKeyPEM(keyPEM)
	if err != nil {
		t.Fatal(err)
	}
	certPEM, err := os.ReadFile(filepath.Join(bundle, "delivery", "token-signing", "tls.crt"))
	if err != nil {
		t.Fatal(err)
	}
	block, rest := pem.Decode(certPEM)
	if block == nil || block.Type != "CERTIFICATE" || len(bytes.TrimSpace(rest)) != 0 {
		t.Fatal("Expected one certificate")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		t.Fatal(err)
	}
	publicDER, err := x509.MarshalPKIXPublicKey(key.PublicKey().CryptoPublicKey())
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(publicDER, cert.RawSubjectPublicKeyInfo) || cert.KeyUsage&x509.KeyUsageDigitalSignature == 0 {
		t.Fatal("Generated certificate does not match the native signing key")
	}
}
