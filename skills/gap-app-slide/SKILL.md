---
name: gap-app-slide
description: "Generate GAP-branded single-slide presentations for technical application modernization overviews. Use this skill whenever Andrea mentions creating slides, presentations, or one-pagers for application data, legacy modernization projects, code metrics, technology stacks, or project statistics that need GAP branding. Trigger on phrases like 'create a slide', 'make a presentation', 'GAP slide', 'application overview', 'modernization summary', or when Andrea provides structured application data (app name, legacy tech, target tech, projects, code size/LOC metrics). Also use when Andrea wants to visualize technical migration data, codebase statistics, or project portfolios in GAP's brand style."
---

# GAP Application Slide Skill

Generate professional, GAP-branded single-slide presentations that showcase application modernization data with clean layouts and proper brand adherence.

## What This Skill Does

Creates a single Google Slide (PowerPoint .pptx format) following Growth Acceleration Partners' official brand guidelines to display:
- Application name and modernization context
- Legacy technologies being replaced
- Target/modern technology stack
- Project counts and portfolio size
- Code size decomposition (lines of code by language)

## When to Use This Skill

Use this skill when Andrea needs to:
- Create a slide for an application modernization overview
- Visualize legacy-to-modern technology transitions
- Display code metrics and project statistics
- Produce GAP-branded technical summaries
- Generate executive-level application data slides

**Trigger phrases:**
- "Create a slide for [Application]"
- "Make a GAP-branded presentation with this data"
- "Generate an application overview slide"
- "Show this modernization data in a slide"
- "Turn this into a GAP slide"

## Input Data Format

The skill expects application data in any clear format, typically including:

**Required:**
- Application name
- Legacy technologies (e.g., "VB6 & C++")
- Target technologies (e.g., ".NET / Angular")

**Optional:**
- Project count
- Code size breakdown by language (LOC - Lines of Code)
- Additional metrics

Example input:
```
Application: Trapeze Software
Legacy Technologies: VB6 & C++
Target Technology: .NET / Angular
Projects: 67
Code Size:
- C++: 4,226,869 LOC
- VB6: 771,092 LOC
```

## Output

A single-slide .pptx file saved to `/mnt/user-data/outputs/` with:
- GAP Blue header band with application name
- Two-column layout (key info left, metrics right)
- Proper GAP color palette and typography
- Clean, professional design following brand guidelines

## Technical Implementation

### Step 1: Load Brand Guidelines

Always start by reading the GAP brand skill to ensure compliance:

```bash
view /mnt/skills/user/gap-brand/SKILL.md
```

Key brand elements to apply:
- **Primary color**: GAP Blue `#006489` for headers
- **Typography**: Proxima Nova (use Arial as fallback in Google Slides)
- **Yellow accent**: `#FEBD12` for max 2 highlight words/numbers only
- **Blue alternates**: Steel Blue `#5497AE`, Soft Blue `#A5CAD6` for visual variety
- **Layout**: Clean, structured with generous whitespace

### Step 2: Verify Dependencies

```bash
npm list -g pptxgenjs || npm install -g pptxgenjs
```

### Step 3: Generate the Slide

Create a Node.js script using PptxGenJS with this structure:

**Slide Layout:**
1. **Header Band (top ~15%)**: GAP Blue background (`#006489`)
   - Application name: 36pt bold, white, left-aligned
   - Subtitle: 18pt regular, white, left-aligned

2. **Left Column**: Key information boxes
   - Legacy Technologies box (light gray background `#F5F5F5`)
   - Target Technology box (light gray background `#F5F5F5`)
   - Projects box (GAP Blue background with yellow number)

3. **Right Column**: Code size metrics
   - Section header in GAP Blue
   - Colored boxes for each language (Steel Blue, Soft Blue)
   - Large numbers (40pt bold) with "Lines of Code" labels

4. **Footer**: "Growth Acceleration Partners" in Warm Gray (`#777373`)

**Code Template:**

```javascript
const PptxGenJS = require("pptxgenjs");
let pres = new PptxGenJS();

pres.layout = "LAYOUT_WIDE";
pres.author = "Growth Acceleration Partners";
pres.title = "[Application] - Modernization Overview";

let slide = pres.addSlide();

// Header band - GAP Blue
slide.addShape(pres.ShapeType.rect, {
  x: 0, y: 0, w: "100%", h: 1.0,
  fill: { color: "006489" },
  line: { type: "none" }
});

// Title and subtitle on header
slide.addText("[Application Name]", {
  x: 0.5, y: 0.3, w: 8.0, h: 0.5,
  fontSize: 36, bold: true, color: "FFFFFF",
  fontFace: "Arial", align: "left", valign: "middle"
});

// [Add left column boxes and right column metrics]

// Footer
slide.addText("Growth Acceleration Partners", {
  x: 0.5, y: 5.2, w: 4.0, h: 0.3,
  fontSize: 10, color: "777373",
  fontFace: "Arial", align: "left", valign: "middle"
});

pres.writeFile({ fileName: "/home/claude/[App_Name]_Overview.pptx" });
```

### Step 4: Quality Assurance

1. **Content verification:**
```bash
extract-text [filename].pptx
```
Verify all data is present and correctly spelled.

2. **Visual inspection:**
```bash
python /mnt/skills/public/pptx/scripts/office/soffice.py --headless --convert-to pdf [filename].pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 150 [filename].pdf slide
ls -1 "$PWD"/slide-*.jpg
```

Then view the slide image to check for:
- Text overflow or cut-off content
- Overlapping elements
- Proper color contrast
- Alignment issues
- Spacing problems

3. **Fix any issues** and re-verify only the affected elements

### Step 5: Deliver to User

```bash
cp /home/claude/[filename].pptx /mnt/user-data/outputs/
```

Then use `present_files` to share with Andrea.

## Design Principles

### Color Usage
- **GAP Blue (`#006489`)**: Header backgrounds, section titles, primary branding
- **Yellow (`#FEBD12`)**: Accent for key numbers ONLY (max 1-2 uses per slide)
- **Steel Blue (`#5497AE`)**: Primary metric boxes
- **Soft Blue (`#A5CAD6`)**: Secondary metric boxes
- **Light Gray (`#F5F5F5`)**: Info box backgrounds
- **Dark Charcoal (`#453F3E`)**: Body text
- **Warm Gray (`#777373`)**: Footer text

### Typography Guidelines
- **Titles**: 36pt bold (header), 20pt bold (sections)
- **Numbers**: 40-48pt bold for large metrics
- **Body text**: 18-24pt regular
- **Labels**: 12-16pt regular
- **Footer**: 10pt regular

### Layout Rules
- **Margins**: Minimum 0.5" from slide edges
- **Spacing**: 0.3-0.5" between content blocks
- **Two-column split**: ~45% left, ~40% right, with gap
- **Alignment**: Left-align text, maintain consistent vertical rhythm

### Avoid
- Don't use accent lines under titles (AI-generated look)
- Don't add decorative bars/ribbons unless explicitly requested
- Don't use yellow as a background color
- Don't overflow text boxes - resize or split content
- Don't use low-contrast combinations (see gap-brand skill for forbidden pairs)

## Customization Options

If Andrea requests variations:
- **Different layouts**: Adjust column widths or switch to single-column
- **Additional metrics**: Add more code language breakdowns or project phases
- **Dark mode**: Use Dark Charcoal background with white text
- **Multiple slides**: Create additional slides for detailed breakdowns

Always maintain GAP brand core identity (Blue, Yellow accent, Proxima Nova/Arial, clean layouts).

## Troubleshooting

**Text overflow:**
- Reduce font size by 2-4pt
- Increase box height by 0.2-0.3"
- Split content across boxes

**Color contrast issues:**
- Verify text/background combinations against forbidden list
- Use white text on dark backgrounds (Blue, Steel Blue, Charcoal)
- Use dark text on light backgrounds (Light Gray, Soft Blue, White)

**Alignment problems:**
- Use consistent x/y coordinates for related elements
- Set explicit width/height for all shapes
- Test vertical spacing with 0.3" or 0.5" gaps

## Examples

### Minimal Input
```
Application: Phoenix System
Legacy: Java 6
Target: Java 17 / Spring Boot
Projects: 12
```

### Rich Input
```
Application: Atlas Platform
Legacy Technologies: COBOL & Mainframe
Target Technology: Python / Microservices
Projects: 156
Code Size Decomposition:
* COBOL: 12,450,892 LOC
* JCL: 1,234,567 LOC
* Assembler: 345,678 LOC
Total: 14,031,137 LOC
```

The skill adapts to whatever data is provided, creating appropriately sized and styled boxes.

## Notes

- Always check gap-brand skill first for latest brand guidelines
- Use `extract-text` and visual inspection for every output
- The yellow accent should highlight key numbers (project counts, totals)
- Keep layouts clean - whitespace is a design feature
- If creating multiple slides for one application, maintain consistent styling
