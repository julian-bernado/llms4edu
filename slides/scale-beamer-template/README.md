# Stanford SCALE Initiative — Beamer Template

A LaTeX Beamer theme that recreates the Stanford SCALE Initiative PowerPoint
template (teal background, Stanford Cardinal Red accent, gear motif, Stanford
SCALE logo footer).

## Files

| File | Purpose |
|------|---------|
| `main.tex` | Demo presentation showing all six layouts |
| `beamerthemescale.sty` | The custom Beamer theme (colors, layouts, footer) |
| `references.bib` | Sample bibliography |
| `stanford-scale-logo.png` | Logo used in the bottom strip |
| `gear-graphic.png` | Original full-opacity gear (kept for reference) |
| `gear-graphic-faded.png` | Subdued (~25% opacity) gear actually used by the theme |

## Using on Overleaf

1. Create a new blank Overleaf project.
2. Upload all files to the project root (drag-and-drop works).
3. Open project settings and set the compiler to **pdfLaTeX**
   (or **XeLaTeX** / **LuaLaTeX** if you want true Arial — see note below).
4. Click *Recompile*. Overleaf will run biber automatically for the
   bibliography.

## Layouts

The demo `main.tex` shows all six:

```latex
% 1. Title slide
\begin{frame}[plain,noframenumbering]\titlepage\end{frame}

% 2. Roadmap (place at start of each \section)
\section{Background}
\roadmapframe                  % default title "Roadmap"
\roadmapframe[Where we are]    % custom title

% 3. Section divider
\sectionframe{Section title}{Optional subtitle}

% 4. Standard content slide (with optional subtitle)
\begin{frame}{Slide Title}
  \framesubtitle{Italic teal subtitle under the bar}
  ...
\end{frame}

% 5. Two-column slide
\begin{frame}{Two-Column Layout}
  \begin{columns}[T,onlytextwidth]
    \begin{column}{0.48\textwidth} ... \end{column}
    \begin{column}{0.48\textwidth} ... \end{column}
  \end{columns}
\end{frame}

% 6. Closing slide
\closingframe{Thank you}{Questions & discussion}
```

### Roadmap behavior

`\roadmapframe` automatically highlights the current section in bold
white with a filled bullet, while other sections appear dimmed (light
teal with hollow bullets). To use it, structure your deck with
`\section{...}` markers and place `\roadmapframe` immediately after each
one.

## Custom commands

| Command | Effect |
|---------|--------|
| `\tealtext{...}` | Inline text in primary teal |
| `\stanfordred{...}` | Inline text in Stanford Cardinal Red |
| `\scalehighlight{...}` | Light-teal highlighted text box |

## Color palette (sampled from the original PPTX)

| Name | Hex | Use |
|------|-----|-----|
| `scaleTeal` | `#009AB4` | Primary background, frame title bar |
| `scaleDarkTeal` | `#1D3457` | Sub-bullets, dark accents |
| `scaleLightTeal` | `#B0D3E1` | Underlines, highlight backgrounds |
| `scaleRed` | `#8C1515` | Stanford Cardinal Red, alert text |
| `scaleGray` | `#7E7775` | Subtle body text, page numbers |

## Fonts

The original deck uses **Arial**. Under pdfLaTeX, the theme falls back to
Helvetica via the `helvet` package — visually nearly identical and the
standard choice for LaTeX-based academic deliverables.

For an exact Arial match, switch the Overleaf compiler to **XeLaTeX** or
**LuaLaTeX** and uncomment the `fontspec` block at the top of
`beamerthemescale.sty`:

```latex
\RequirePackage{fontspec}
\setsansfont{Arial}
\setmainfont{Arial}
```

## Gear graphic notes

The theme uses `gear-graphic-faded.png` (the original at ~25% opacity)
so the wheel reads as a subtle background motif rather than a competing
focal element, matching the look of the source PPTX. The gear is also
**clipped at the teal/white boundary** on title and closing slides so
it never spills onto the white logo strip.

The gear is **scaled differently per layout** to stay proportional:

- Title / closing slides: 0.42 of paper width (the white logo strip
  takes a noticeable chunk of vertical space)
- Section dividers: 0.55 (full-bleed teal background)
- Roadmap: 0.50 (similar to section, leaves room for TOC text)

If you need to swap in your own gear or use a different opacity, edit
the file `gear-graphic-faded.png` directly, or override
`\scalegearfaded` in your preamble:

```latex
\renewcommand{\scalegearfaded}{your-image.png}
```

## Bibliography

The demo uses `biblatex` with the `biber` backend (Overleaf's default).
The current `\nocite{*}` line in `main.tex` forces all entries in
`references.bib` to appear; remove it once you have real `\cite{...}`
calls in your slides.
