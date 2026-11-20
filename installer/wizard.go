package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"strings"
)

type prompts struct {
	input *bufio.Scanner
	out   io.Writer
	err   error
}

func (p *prompts) ask(question string) string {
	if p.err != nil {
		return ""
	}
	fmt.Fprint(p.out, question, " ")
	if !p.input.Scan() {
		p.err = p.input.Err()
		if p.err == nil {
			p.err = fmt.Errorf("input ended; run vault --help for noninteractive commands")
		}
		return ""
	}
	return strings.TrimSpace(p.input.Text())
}
func (p *prompts) yes(question string) bool {
	for p.err == nil {
		switch strings.ToLower(p.ask(question + " [y/N]")) {
		case "y", "yes":
			return true
		case "", "n", "no":
			return false
		}
		fmt.Fprintln(p.out, "Enter y or n.")
	}
	return false
}
func wizard(in io.Reader, out io.Writer) (options, error) {
	p := prompts{input: bufio.NewScanner(in), out: out}
	var o options
	for o.action == "" && p.err == nil {
		switch p.ask("1. Create a vault\n2. Update a vault\n3. Prepare tools on this device\nChoose [1-3]:") {
		case "1":
			o.action = "init"
		case "2":
			o.action = "update"
		case "3":
			o.action = "prepare"
		default:
			if p.err == nil {
				fmt.Fprintln(out, "Enter 1, 2, or 3.")
			}
		}
	}
	for o.root == "" && p.err == nil {
		path := p.ask("Vault directory:")
		if p.err != nil {
			break
		}
		root, err := vaultPath(path)
		if err == nil && o.action == "init" {
			_, err = checkDestination(root)
		}
		if err != nil {
			fmt.Fprintln(out, err)
			continue
		}
		o.root = root
	}
	if o.action == "init" {
		o.obsidian = p.yes("Include Obsidian settings?")
		o.git = p.yes("Initialize Git?")
	}
	if o.action != "prepare" {
		o.tools = p.yes("Include the Python maintenance tools?")
	}
	if o.tools && p.err == nil {
		if python() == nil {
			fmt.Fprintln(out, missingPython)
		} else {
			o.prepare = p.yes("Install tool dependencies on this device now?")
		}
	}
	if o.action == "prepare" || (o.prepare && (o.git || o.action == "update")) {
		o.hook = p.yes("Install the Git commit hooks?")
	}
	if p.err != nil {
		return options{}, p.err
	}
	fmt.Fprintln(out, "Planned:", o.preview())
	if o.prepare {
		fmt.Fprintln(out, "Then:", (options{action: "prepare", root: o.root, hook: o.hook}).preview())
	}
	if !p.yes("Proceed?") {
		return options{}, p.err
	}
	return o, nil
}

// Render the same flags accepted by the direct command.
func (o options) preview() string {
	f, _ := o.flags() // The wizard only produces known actions.
	parts := []string{"vault", o.action, fmt.Sprintf("%q", o.root)}
	f.VisitAll(func(opt *flag.Flag) {
		if opt.Name == "ref" {
			if o.ref != "" {
				parts = append(parts, "--ref", fmt.Sprintf("%q", o.ref))
			}
			return
		}
		if opt.Value.String() == "true" {
			parts = append(parts, "--"+opt.Name)
		}
	})
	return strings.Join(parts, " ")
}
