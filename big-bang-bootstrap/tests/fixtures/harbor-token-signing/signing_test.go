package signing_test

import (
	"bytes"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"strings"
	"testing"
	"time"

	"github.com/docker/libtrust"
)

// Actual Harbor 2.15.2 dependency, not a Python approximation of its parser.
// src/core/service/token/authutils.go calls UnmarshalPrivateKeyPEM then KeyID.
func TestHarborTokenSigningEncoding(t *testing.T) {
	key, err := rsa.GenerateKey(rand.Reader, 3072)
	if err != nil {
		t.Fatal(err)
	}
	pkcs8, err := x509.MarshalPKCS8PrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	bad := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: pkcs8})
	if _, err := libtrust.UnmarshalPrivateKeyPEM(bad); err == nil || err.Error() != "unable to get PrivateKey from PEM type: PRIVATE KEY" {
		t.Fatalf("PKCS#8 did not reproduce the native failure: %v", err)
	}
	// A header-only edit is not conversion and cannot satisfy the native parser.
	disguised := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: pkcs8})
	if _, err := libtrust.UnmarshalPrivateKeyPEM(disguised); err == nil || !strings.Contains(err.Error(), "unable to decode RSA Private Key PEM data") {
		t.Fatalf("Relabelled PKCS#8 was not rejected: %v", err)
	}
	parsed, err := x509.ParsePKCS8PrivateKey(pkcs8)
	if err != nil {
		t.Fatal(err)
	}
	converted := parsed.(*rsa.PrivateKey)
	good := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(converted)})
	native, err := libtrust.UnmarshalPrivateKeyPEM(good)
	if err != nil {
		t.Fatal(err)
	}
	originalPublic, err := libtrust.FromCryptoPublicKey(&key.PublicKey)
	if err != nil {
		t.Fatal(err)
	}
	if native.KeyID() != originalPublic.KeyID() {
		t.Fatal("Same-key conversion changed JWT kid")
	}
	beforeDER, err := x509.MarshalPKIXPublicKey(&key.PublicKey)
	if err != nil {
		t.Fatal(err)
	}
	afterDER, err := x509.MarshalPKIXPublicKey(native.PublicKey().CryptoPublicKey())
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(beforeDER, afterDER) {
		t.Fatal("Conversion changed public key")
	}
	certTemplate := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Synthetic Harbor signer"},
		NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), KeyUsage: x509.KeyUsageDigitalSignature}
	certDER, err := x509.CreateCertificate(rand.Reader, certTemplate, certTemplate, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	cert, err := x509.ParseCertificate(certDER)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(cert.RawSubjectPublicKeyInfo, afterDER) {
		t.Fatal("Original certificate no longer matches")
	}
	digest := sha256.Sum256([]byte("synthetic Harbor token signature preservation"))
	signature, err := rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatal(err)
	}
	if err := rsa.VerifyPKCS1v15(cert.PublicKey.(*rsa.PublicKey), crypto.SHA256, digest[:], signature); err != nil {
		t.Fatal(err)
	}
	convertedSignature, err := rsa.SignPKCS1v15(rand.Reader, converted, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(signature, convertedSignature) {
		t.Fatal("Same-key RS256 signature changed")
	}
}
