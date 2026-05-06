// Package cmd — note subcommand for managing tech lead notes.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/unrealandychan/rekipedia/internal/storage"
)

var noteCmd = &cobra.Command{
	Use:   "note",
	Short: "Manage tech lead notes",
}

var noteAddCmd = &cobra.Command{
	Use:   "add <content>",
	Short: "Add a new tech lead note",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		tag, _ := cmd.Flags().GetString("tag")
		store, err := openStore()
		if err != nil {
			return err
		}
		defer store.Close()
		id, err := store.UpsertNote(args[0], tag, "manual")
		if err != nil {
			return err
		}
		fmt.Printf("Note added: %s\n", id)
		return nil
	},
}

var noteListCmd = &cobra.Command{
	Use:   "list",
	Short: "List tech lead notes",
	RunE: func(cmd *cobra.Command, args []string) error {
		tag, _ := cmd.Flags().GetString("tag")
		asJSON, _ := cmd.Flags().GetBool("json")
		store, err := openStore()
		if err != nil {
			return err
		}
		defer store.Close()
		notes, err := store.ListNotes(tag)
		if err != nil {
			return err
		}
		if asJSON {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			return enc.Encode(notes)
		}
		if len(notes) == 0 {
			fmt.Println("No notes found.")
			return nil
		}
		for _, n := range notes {
			tagPfx := ""
			if n.Tags != "" {
				tagPfx = fmt.Sprintf("[%s] ", n.Tags)
			}
			content := n.Content
			if len(content) > 80 {
				content = content[:80]
			}
			fmt.Printf("%s  %s%s\n", n.ID[:8], tagPfx, content)
		}
		return nil
	},
}

var noteRemoveCmd = &cobra.Command{
	Use:   "remove <id>",
	Short: "Remove a note by ID",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		store, err := openStore()
		if err != nil {
			return err
		}
		defer store.Close()
		deleted, err := store.DeleteNote(args[0])
		if err != nil {
			return err
		}
		if deleted {
			fmt.Printf("Deleted note %s\n", args[0])
		} else {
			return fmt.Errorf("note not found: %s", args[0])
		}
		return nil
	},
}

func openStore() (*storage.Store, error) {
	repoRoot, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	dbPath := filepath.Join(repoRoot, outputDir, "store.db")
	return storage.Open(dbPath)
}

func init() {
	noteAddCmd.Flags().String("tag", "", "Comma-separated tags")
	noteListCmd.Flags().String("tag", "", "Filter by tag")
	noteListCmd.Flags().Bool("json", false, "Output JSON array")

	noteCmd.AddCommand(noteAddCmd, noteListCmd, noteRemoveCmd)
}
