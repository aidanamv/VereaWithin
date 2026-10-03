# Website Images — Verea Within

Place your image files in **this folder** (`site/assets/`) using these exact
file names, and they will automatically appear across the whole website.

## Required files

| File name          | Where it appears                                              | Recommended size            |
|--------------------|--------------------------------------------------------------|-----------------------------|
| `logo.jpeg`        | Header (top-left) and footer on every page                   | Square, 200×200px or larger |
| `founder.png`      | Hero portrait on the homepage, packages page & booking page  | Portrait 3:4, e.g. 900×1200px |

## Notes

- **Logo**: if `logo.jpeg` is missing, the site automatically falls back to a
  small brown circle with the letter "V", so nothing breaks.
- **Founder photo**: if `founder.png` is missing, a soft gradient placeholder
  with an icon is shown instead.
- You can use `.jpg`, `.jpeg`, or `.png` for the founder photo — just keep the
  name `founder.png` (or update the `src` in the HTML if you prefer a different
  extension).
- After adding the files, hard-refresh your browser (Ctrl+F5) to clear the
  cached placeholders.

## Example

```
site/
  assets/
    logo.jpeg       <-- your round brand logo
    founder.png     <-- your portrait / profile photo
  index.html
  packages.html
  consultation.html
```
