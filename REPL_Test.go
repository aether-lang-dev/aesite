package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	// Echo instance
	e := echo.New()

	// Middleware
	e.Use(middleware.RequestLoggerWithConfig(middleware.RequestLoggerConfig{
		LogStatus: true,
		LogURI:    true,
		LogMethod: true,
		LogValuesFunc: func(c echo.Context, v middleware.RequestLoggerValues) error {
			log.Printf("%s %s %d", v.Method, v.URI, v.Status)
			return nil
		},
	}))
	e.Use(middleware.Recover())

	// Static files
	e.Static("/static", "static")
	e.Static("/Docs", "static/Docs")
	e.Static("/", "static")

	// Routes
	e.File("/", "static/repl.html")
	e.GET("/api/lesson/:nbr", getLesson)
	e.PUT("/api/exec", executeCode)

	// Start server
	e.Logger.Fatal(e.Start(":1323"))
}

type LessonResponse struct {
	Title       string `json:"title"`
	Theory      string `json:"theory"`
	StarterCode string `json:"starter_code"`
}

func getLesson(c echo.Context) error {
	nbr := c.Param("nbr")

	theoryBytes, err := os.ReadFile(filepath.Join("resources", "lessons", nbr, "content.html"))
	if err != nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": fmt.Sprintf("lesson %s not found", nbr)})
	}

	codeBytes, err := os.ReadFile(filepath.Join("resources", "lessons", nbr, "code.ea"))
	if err != nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": fmt.Sprintf("lesson %s code not found", nbr)})
	}

	title := fmt.Sprintf("Lesson %s", nbr)
	if titleBytes, err := os.ReadFile(filepath.Join("resources", "lessons", nbr, "title.txt")); err == nil {
		title = string(titleBytes)
	}

	resp := LessonResponse{
		Title:       title,
		Theory:      string(theoryBytes),
		StarterCode: string(codeBytes),
	}
	return c.JSON(http.StatusOK, resp)
}

type ExecRequest struct {
	UserCode string `json:"user_code"`
}

type ExecResponse struct {
	Stdout string `json:"stdout"`
	Stderr string `json:"stderr"`
}

func executeCode(c echo.Context) error {
	req := new(ExecRequest)
	if err := c.Bind(req); err != nil {
		return err
	}

	// Mock execution result
	resp := ExecResponse{
		Stdout: "Hello, Aether!\nProgram executed successfully.",
		Stderr: "warning: variable 'x' is unused",
	}
	return c.JSON(http.StatusOK, resp)
}
