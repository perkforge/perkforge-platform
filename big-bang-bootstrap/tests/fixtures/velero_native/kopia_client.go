package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"github.com/kopia/kopia/fs/localfs"
	"github.com/kopia/kopia/repo"
	"github.com/kopia/kopia/repo/blob/s3"
	"github.com/kopia/kopia/repo/content"
	"github.com/kopia/kopia/repo/maintenance"
	"github.com/kopia/kopia/repo/manifest"
	"github.com/kopia/kopia/snapshot"
	"github.com/kopia/kopia/snapshot/policy"
	"github.com/kopia/kopia/snapshot/restore"
	"github.com/kopia/kopia/snapshot/snapshotfs"
	"github.com/kopia/kopia/snapshot/snapshotmaintenance"
	"github.com/kopia/kopia/snapshot/upload"
	"os"
	"path/filepath"
	"time"
)

type State struct {
	Manifest string `json:"manifest"`
	Root     string `json:"root"`
	Hash     string `json:"hash"`
	Size     int    `json:"size"`
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}
func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	root := os.Getenv("PROBE_ROOT")
	if root == "" {
		panic("missing PROBE_ROOT")
	}
	op := os.Args[1]
	ca, err := os.ReadFile(filepath.Join(root, "runtime/tls.crt"))
	check(err)
	raw, err := os.ReadFile(filepath.Join(root, "runtime/key.json"))
	check(err)
	var key map[string]string
	check(json.Unmarshal(raw, &key))
	pw, err := os.ReadFile(filepath.Join(root, "runtime/repository-password"))
	check(err)
	opts := s3.Options{BucketName: "velero-probe", Prefix: "kopia/", Endpoint: "localhost:44390", Region: "garage", AccessKeyID: key["id"], SecretAccessKey: key["secret"], RootCA: ca}

	if op == "negative" {
		for _, name := range []string{"wrong-ca", "wrong-host", "wrong-credentials", "other-bucket"} {
			bad := opts
			switch name {
			case "wrong-ca":
				bad.RootCA = nil
			case "wrong-host":
				bad.Endpoint = "127.0.0.1:44390"
			case "wrong-credentials":
				bad.AccessKeyID = "GK000000000000000000000000"
				bad.SecretAccessKey = "synthetic-wrong-key"
			case "other-bucket":
				bad.BucketName = "other-probe"
			}
			c, stop := context.WithTimeout(ctx, 8*time.Second)
			b, e := s3.New(c, &bad, false)
			if e == nil {
				e = repo.Connect(c, filepath.Join(root, "runtime", "negative-"+name+".json"), b, string(pw), nil)
				b.Close(c)
			}
			stop()
			if e == nil {
				panic("negative unexpectedly accepted: " + name)
			}
			fmt.Printf("DENIED %s: %v\n", name, e)
		}
		return
	}
	st, err := s3.New(ctx, &opts, false)
	check(err)
	defer st.Close(ctx)
	if op == "create" {
		check(repo.Initialize(ctx, st, &repo.NewRepositoryOptions{}, string(pw)))
	}
	cfg := filepath.Join(root, "runtime", "kopia-"+op+".config")
	cache := filepath.Join(root, "runtime", "cache-"+op)
	check(repo.Connect(ctx, cfg, st, string(pw), &repo.ConnectOptions{ClientOptions: repo.ClientOptions{Username: "synthetic", Hostname: "probe"}, CachingOptions: content.CachingOptions{CacheDirectory: cache}}))
	r, err := repo.Open(ctx, cfg, string(pw), nil)
	check(err)
	defer r.Close(ctx)
	statePath := filepath.Join(root, "runtime/snapshot-state.json")
	var state State
	if op != "create" {
		raw, err = os.ReadFile(statePath)
		check(err)
		check(json.Unmarshal(raw, &state))
	}
	switch op {
	case "create":
		src := filepath.Join(root, "synthetic-input")
		check(os.Mkdir(src, 0700))
		data := make([]byte, 17*1024*1024)
		_, err = rand.Read(data)
		check(err)
		check(os.WriteFile(filepath.Join(src, "payload.bin"), data, 0600))
		sum := sha256.Sum256(data)
		state.Hash = hex.EncodeToString(sum[:])
		state.Size = len(data)
		check(repo.WriteSession(ctx, r, repo.WriteSessionOptions{Purpose: "synthetic snapshot"}, func(ctx context.Context, w repo.RepositoryWriter) error {
			entry, e := localfs.NewEntry(src)
			if e != nil {
				return e
			}
			source := snapshot.SourceInfo{UserName: "synthetic", Host: "probe", Path: "/synthetic"}
			tree, e := policy.TreeForSource(ctx, w, source)
			if e != nil {
				return e
			}
			m, e := upload.NewUploader(w).Upload(ctx, entry, tree, source)
			if e != nil {
				return e
			}
			if m.IncompleteReason != "" {
				return fmt.Errorf("incomplete snapshot: %s", m.IncompleteReason)
			}
			id, e := snapshot.SaveSnapshot(ctx, w, m)
			state.Manifest = string(id)
			state.Root = m.RootEntry.ObjectID.String()
			return e
		}))
		encoded, _ := json.Marshal(state)
		check(os.WriteFile(statePath, encoded, 0600))
		fmt.Println("PASS exact pinned Kopia initialized, uploaded and saved snapshot", state.Size)
	case "restore", "restore-after-maintenance":
		m, e := snapshot.LoadSnapshot(ctx, r, manifest.ID(state.Manifest))
		check(e)
		if m.RootEntry.ObjectID.String() != state.Root {
			panic("manifest root changed")
		}
		entry, e := snapshotfs.FilesystemEntryFromIDWithPath(ctx, r, state.Root, false)
		check(e)
		out := &restore.FilesystemOutput{TargetPath: filepath.Join(root, op), SkipOwners: true}
		check(out.Init(ctx))
		_, e = restore.Entry(ctx, r, out, entry, restore.Options{Parallel: 2, RestoreDirEntryAtDepth: 2147483647})
		check(e)
		data, e := os.ReadFile(filepath.Join(root, op, "payload.bin"))
		check(e)
		sum := sha256.Sum256(data)
		if len(data) != state.Size || hex.EncodeToString(sum[:]) != state.Hash {
			panic("restore hash mismatch")
		}
		fmt.Println("PASS independent fresh-cache restore SHA256", state.Size)
	case "maintenance", "cleanup":
		dr, ok := r.(repo.DirectRepository)
		if !ok {
			panic("not direct repo")
		}
		check(repo.DirectWriteSession(ctx, dr, repo.WriteSessionOptions{Purpose: "synthetic maintenance"}, func(ctx context.Context, w repo.DirectRepositoryWriter) error {
			p := maintenance.DefaultParams()
			p.Owner = w.ClientOptions().UsernameAtHost()
			if e := maintenance.SetParams(ctx, w, &p); e != nil {
				return e
			}
			if op == "cleanup" {
				if e := w.DeleteManifest(ctx, manifest.ID(state.Manifest)); e != nil {
					return e
				}
			}
			return snapshotmaintenance.Run(ctx, w, maintenance.ModeFull, true, maintenance.SafetyFull)
		}))
		fmt.Println("PASS full maintenance with upstream safety", op)
	default:
		panic("bad operation")
	}
}
