# Aether Language — Website & REPL Demo

A demo project showcasing the website and interactive REPL for the **Aether** programming language. Built with Go and the Echo framework.

## Overview

This project serves as a full demo of the Aether language website, including a working interactive REPL page where users can read lesson theory and experiment with starter code. The backend is intentionally minimal — code execution is currently mocked, as the final backend will be written in Aether. This project made it possible to implement and test the REPL frontend.

## Features

- Static website pages served via Echo (`index.html`, `faq.html`, `articles.html`, `docs.html`, `tutorials.html`)
- Interactive REPL page (`/`) with a split theory/editor layout
- Lesson system: theory content and starter code loaded dynamically from `/api/lesson/:nbr`
- Resizable output pane displaying stdout and stderr
- Lesson navigation (previous/next) with page indicator
- Mock code execution endpoint (`PUT /api/exec`) returning stdout and stderr

## Project Structure

```
REPL_Test.go          # Main Go server (Echo)
static/               # All HTML pages and CSS
resources/
  lessons/
    1/                # content.html, code.ea, title.txt
    2/                # content.html, code.ea, title.txt
```

## Running

```bash
go run REPL_Test.go
```

Server starts at `http://localhost:1323`.

## Stack

- **Backend:** Go, [Echo v4](https://echo.labstack.com/)
- **Frontend:** Vanilla HTML/CSS/JS, DM font family
