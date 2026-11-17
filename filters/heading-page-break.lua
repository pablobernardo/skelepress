-- A heading with the {.page-break} class starts a new page.
--
-- LaTeX: emit \clearpage before the heading and drop the marker class, so no
-- unknown class survives into the typeset output. Every other format keeps the
-- class untouched: HTML and EPUB stylesheets turn it into a CSS break-before
-- hook instead of embedding format-specific markup in the sources.
--
-- Two properties are deliberate:
--
-- 1. Consecutive breaks are safe. \clearpage right after another \clearpage
--    (for example the merge-level chapter break) never ships a blank page.
-- 2. Nothing is format-specific in the sources. One heading class travels with
--    the chapter across formats and reordering, unlike raw \clearpage.
--
-- Output is identical when no heading carries the class.
local PAGE_BREAK_CLASS = "page-break"

local function tex_output()
  return FORMAT == "latex" or FORMAT == "beamer"
end

function Header(header)
  if not header.classes:includes(PAGE_BREAK_CLASS) then
    return nil
  end
  if not tex_output() then
    return nil
  end
  local remaining = pandoc.List({})
  for _, class in ipairs(header.classes) do
    if class ~= PAGE_BREAK_CLASS then
      remaining:insert(class)
    end
  end
  header.classes = remaining
  return { pandoc.RawBlock("latex", "\\clearpage"), header }
end
