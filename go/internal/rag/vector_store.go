package rag

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
)

// VectorStore is a pure in-memory cosine-similarity vector store.
type VectorStore struct {
	chunks  []Chunk
	vectors [][]float32
}

// SearchResult holds a matched chunk and its similarity score.
type SearchResult struct {
	Chunk Chunk   `json:"chunk"`
	Score float32 `json:"score"`
}

// NewVectorStore creates an empty VectorStore.
func NewVectorStore() *VectorStore {
	return &VectorStore{}
}

// Add inserts a chunk with its embedding vector.
func (v *VectorStore) Add(chunk Chunk, embedding []float32) {
	v.chunks = append(v.chunks, chunk)
	v.vectors = append(v.vectors, embedding)
}

// Len returns the number of stored vectors.
func (v *VectorStore) Len() int { return len(v.chunks) }

// Search returns the top-K most similar chunks to the query vector.
func (v *VectorStore) Search(query []float32, topK int) []SearchResult {
	if len(v.chunks) == 0 {
		return nil
	}
	type scored struct {
		idx   int
		score float32
	}
	scores := make([]scored, len(v.chunks))
	for i, vec := range v.vectors {
		scores[i] = scored{i, cosine(query, vec)}
	}
	sort.Slice(scores, func(a, b int) bool { return scores[a].score > scores[b].score })
	if topK > len(scores) {
		topK = len(scores)
	}
	results := make([]SearchResult, topK)
	for i := 0; i < topK; i++ {
		results[i] = SearchResult{Chunk: v.chunks[scores[i].idx], Score: scores[i].score}
	}
	return results
}

// Save writes chunks.json and vectors.bin to dir.
func (v *VectorStore) Save(dir string) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	// chunks.json
	data, err := json.Marshal(v.chunks)
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dir, "chunks.json"), data, 0o644); err != nil {
		return err
	}
	// vectors.bin: [n uint32][dim uint32][n*dim float32]
	f, err := os.Create(filepath.Join(dir, "vectors.bin"))
	if err != nil {
		return err
	}
	defer f.Close()
	n := uint32(len(v.vectors))
	dim := uint32(0)
	if n > 0 {
		dim = uint32(len(v.vectors[0]))
	}
	if err := binary.Write(f, binary.LittleEndian, n); err != nil {
		return err
	}
	if err := binary.Write(f, binary.LittleEndian, dim); err != nil {
		return err
	}
	for _, vec := range v.vectors {
		if uint32(len(vec)) != dim {
			return fmt.Errorf("vector dimension mismatch: expected %d got %d", dim, len(vec))
		}
		if err := binary.Write(f, binary.LittleEndian, vec); err != nil {
			return err
		}
	}
	return nil
}

// Load reads chunks.json and vectors.bin from dir.
func (v *VectorStore) Load(dir string) error {
	data, err := os.ReadFile(filepath.Join(dir, "chunks.json"))
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, &v.chunks); err != nil {
		return err
	}
	f, err := os.Open(filepath.Join(dir, "vectors.bin"))
	if err != nil {
		return err
	}
	defer f.Close()
	var n, dim uint32
	if err := binary.Read(f, binary.LittleEndian, &n); err != nil {
		return err
	}
	if err := binary.Read(f, binary.LittleEndian, &dim); err != nil {
		return err
	}
	v.vectors = make([][]float32, n)
	for i := range v.vectors {
		vec := make([]float32, dim)
		if err := binary.Read(f, binary.LittleEndian, vec); err != nil {
			return err
		}
		v.vectors[i] = vec
	}
	return nil
}

func cosine(a, b []float32) float32 {
	if len(a) != len(b) || len(a) == 0 {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return float32(dot / denom)
}
