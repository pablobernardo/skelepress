-- Rewrite image paths for the WebP copies the HTML render converted.
--
-- HTML only. The renderer converts declared raster images to WebP before
-- pandoc reads the merged markdown, writes the copies to a working directory,
-- and stores the mapping `resolved original path -> WebP copy` in
-- SKELEPRESS_WEBP_MAP as one `original<TAB>copy` pair per line (tabs and
-- newlines cannot appear in a path; JSON is unavailable inside pandoc's Lua
-- environment). Markdown image targets reach this filter still unresolved
-- (project-relative or absolute); the filter normalises the target the way
-- pandoc resolves it: against the working directory first, then each
-- --resource-path entry in declared order, and swaps in the WebP copy at the
-- first hit. Unmapped images fall through untouched.
--
-- Output is identical when SKELEPRESS_WEBP_MAP is absent or empty. A data
-- URI or remote URL needs no conversion and never matches a mapping.

local raw = os.getenv("SKELEPRESS_WEBP_MAP") or ""
local raw_paths = os.getenv("SKELEPRESS_WEBP_RESOURCE_PATH") or ""

local mappings = {}
local original, copy
for line in raw:gmatch("[^\n]+") do
  original, copy = line:match("^([^\t]*)\t(.*)$")
  if original and copy and original ~= "" then
    mappings[original] = copy
  end
end

-- One resource-path entry per line, matching the pandoc argv order.
local resource_paths = {}
for entry in raw_paths:gmatch("[^\n]+") do
  resource_paths[#resource_paths + 1] = entry
end

if next(mappings) == nil then
  return {}
end

local wd = pandoc.system.get_working_directory()

-- Collapse `.` and `..` segments like a resolved path would read.
local function collapse(absolute)
  local parts = {}
  for part in absolute:gmatch("[^/]+") do
    if part == ".." and #parts > 0 and parts[#parts] ~= ".." then
      parts[#parts] = nil
    elseif part ~= "." then
      parts[#parts + 1] = part
    end
  end
  return "/" .. table.concat(parts, "/")
end

local function normalize(target)
  if target:sub(1, 5) == "data:" or target:sub(1, 7) == "http://" or target:sub(1, 8) == "https://" then
    return nil
  end
  if target:sub(1, 1) == "/" then
    return collapse(target)
  end
  return collapse(wd .. "/" .. target)
end

local function rewrite(image)
  local mapped = mappings[normalize(image.src)]
  if mapped == nil and image.src:sub(1, 1) ~= "/" then
    for _, entry in ipairs(resource_paths) do
      mapped = mappings[normalize(entry .. "/" .. image.src)]
      if mapped ~= nil then
        break
      end
    end
  end
  if mapped ~= nil then
    image.src = mapped
  end
  return image
end

return {
  {
    Image = rewrite,
  },
}
