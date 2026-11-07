package main

import (
	"bytes"
	"crypto/sha256"
	"github.com/sirupsen/logrus"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"
)

const regionKey = "region"

func TestGarageExactPlugin(t *testing.T) {
	root := os.Getenv("PROBE_ROOT")
	if root == "" {
		t.Fatal("PROBE_ROOT missing")
	}
	for _, k := range []string{"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_ROLE_ARN", "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_CONTAINER_CREDENTIALS_FULL_URI"} {
		t.Setenv(k, "")
	}
	t.Setenv("AWS_EC2_METADATA_DISABLED", "true")
	t.Setenv("AWS_MAX_ATTEMPTS", "1")
	ca, e := os.ReadFile(filepath.Join(root, "runtime/tls.crt"))
	if e != nil {
		t.Fatal(e)
	}
	config := func() map[string]string {
		return map[string]string{"region": "garage", "s3Url": "https://localhost:44390", "s3ForcePathStyle": "true", "credentialsFile": filepath.Join(root, "runtime/aws-credentials"), "caCert": string(ca), "bucket": "velero-probe", "insecureSkipTLSVerify": "false"}
	}
	s := newObjectStore(logrus.New())
	if e = s.Init(config()); e != nil {
		t.Fatal(e)
	}
	if s.checksumAlg != "CRC32" {
		t.Fatalf("wrong checksum %s", s.checksumAlg)
	}
	for _, size := range []int{4096, 11 * 1024 * 1024} {
		t.Run("roundtrip", func(t *testing.T) {
			payload := make([]byte, size)
			for i := range payload {
				payload[i] = byte((i*17 + i/251) % 256)
			}
			key := "metadata/roundtrip"
			if e := s.PutObject("velero-probe", key, bytes.NewReader(payload)); e != nil {
				t.Fatal(e)
			}
			ok, e := s.ObjectExists("velero-probe", key)
			if e != nil || !ok {
				t.Fatalf("head %v %v", ok, e)
			}
			r, e := s.GetObject("velero-probe", key)
			if e != nil {
				t.Fatal(e)
			}
			got, e := io.ReadAll(r)
			r.Close()
			if e != nil || sha256.Sum256(got) != sha256.Sum256(payload) {
				t.Fatal("hash mismatch", e)
			}
			objs, e := s.ListObjects("velero-probe", "metadata/")
			if e != nil || len(objs) != 1 {
				t.Fatalf("list %v %v", objs, e)
			}
			pre, e := s.ListCommonPrefixes("velero-probe", "", "/")
			found := false
			for _, v := range pre {
				if v == "metadata/" {
					found = true
				}
			}
			if e != nil || !found {
				t.Fatalf("prefix %v %v", pre, e)
			}
			if _, e = s.CreateSignedURL("velero-probe", key, time.Minute); e != nil {
				t.Fatal(e)
			}
			if e = s.DeleteObject("velero-probe", key); e != nil {
				t.Fatal(e)
			}
			ok, e = s.ObjectExists("velero-probe", key)
			if e != nil || ok {
				t.Fatalf("delete %v %v", ok, e)
			}
		})
	}
	t.Run("other-bucket-denied", func(t *testing.T) {
		if e := s.PutObject("other-probe", "must-not-exist", bytes.NewReader([]byte("deny"))); e == nil {
			t.Fatal("unscoped bucket write accepted")
		}
	})
	t.Run("wrong-ca-denied", func(t *testing.T) {
		c := config()
		delete(c, "caCert")
		x := newObjectStore(logrus.New())
		if e := x.Init(c); e != nil {
			t.Fatal(e)
		}
		if e := x.PutObject("velero-probe", "must-not-exist", bytes.NewReader([]byte("deny"))); e == nil {
			t.Fatal("untrusted TLS accepted")
		}
	})
	t.Run("wrong-host-denied", func(t *testing.T) {
		c := config()
		c["s3Url"] = "https://127.0.0.1:44390"
		x := newObjectStore(logrus.New())
		if e := x.Init(c); e != nil {
			t.Fatal(e)
		}
		if e := x.PutObject("velero-probe", "must-not-exist", bytes.NewReader([]byte("deny"))); e == nil {
			t.Fatal("wrong TLS hostname accepted")
		}
	})
	t.Run("wrong-credentials-denied", func(t *testing.T) {
		f := filepath.Join(t.TempDir(), "bad-creds")
		os.WriteFile(f, []byte("[default]\naws_access_key_id=GK000000000000000000000000\naws_secret_access_key=synthetic-wrong-key\n"), 0600)
		c := config()
		c["credentialsFile"] = f
		x := newObjectStore(logrus.New())
		if e := x.Init(c); e != nil {
			t.Fatal(e)
		}
		if e := x.PutObject("velero-probe", "must-not-exist", bytes.NewReader([]byte("deny"))); e == nil {
			t.Fatal("wrong credentials accepted")
		}
	})
}
