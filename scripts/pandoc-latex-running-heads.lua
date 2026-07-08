-- Pandoc Lua filter for CME LaTeX running heads.
--
-- The book frontmatter header defines a cmebody page style.  This filter keeps
-- running-head text short enough for 5x8 pages by setting a short book title and
-- short section marks after generated headings.  Full headings remain visible in
-- the body/ToC; only the running-head marks are shortened.

local max_running_head_chars = 42
local min_delimiter_cut_chars = 12

local function trim(text)
  return (text:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function normalize_space(text)
  return trim((text or ""):gsub("%s+", " "))
end

local function utf8_chars(text)
  local chars = {}
  for _, codepoint in utf8.codes(text) do
    chars[#chars + 1] = utf8.char(codepoint)
  end
  return chars
end

local function utf8_length(text)
  local ok, length = pcall(function()
    return utf8.len(text)
  end)
  if ok and length then
    return length
  end
  return #text
end

local function utf8_sub(text, first, last)
  local chars = utf8_chars(text)
  local parts = {}
  local final = last or #chars
  for index = first, math.min(final, #chars) do
    parts[#parts + 1] = chars[index]
  end
  return table.concat(parts)
end

local function last_delimiter_cut(text)
  local best = nil
  local patterns = {
    "%s%-%-+%s",
    "%s%-/%-%s",
    "%s:%s",
    ":%s",
    ";%s",
    "%.%s",
    ",%s",
  }
  for _, pattern in ipairs(patterns) do
    local start = 1
    while true do
      local first = text:find(pattern, start)
      if not first then
        break
      end
      if utf8_length(text:sub(1, first - 1)) >= min_delimiter_cut_chars then
        best = first - 1
      end
      start = first + 1
    end
  end
  return best
end

local function shorten_text(text)
  local normalized = normalize_space(text)
  if normalized == "" or utf8_length(normalized) <= max_running_head_chars then
    return normalized
  end

  local prefix = utf8_sub(normalized, 1, max_running_head_chars)
  local delimiter_cut = last_delimiter_cut(prefix)
  if delimiter_cut then
    prefix = trim(prefix:sub(1, delimiter_cut))
  else
    local space_cut = prefix:match("^(.+)%s+%S*$")
    if space_cut and utf8_length(space_cut) >= min_delimiter_cut_chars then
      prefix = trim(space_cut)
    else
      prefix = trim(prefix)
    end
  end

  prefix = prefix:gsub("[%s,;:%-]+$", "")
  if prefix == "" then
    prefix = utf8_sub(normalized, 1, max_running_head_chars)
  end
  return prefix .. "..."
end

local tex_escapes = {
  ["\\"] = "\\textbackslash{}",
  ["{"] = "\\{",
  ["}"] = "\\}",
  ["$"] = "\\$",
  ["&"] = "\\&",
  ["%"] = "\\%",
  ["#"] = "\\#",
  ["_"] = "\\_",
  ["^"] = "\\textasciicircum{}",
  ["~"] = "\\textasciitilde{}",
}

local function escape_tex(text)
  return text:gsub("[\\{}$&%%#_^~]", tex_escapes)
end

local function stringify_meta_value(value)
  if not value then
    return ""
  end
  if type(value) == "table" then
    return pandoc.utils.stringify(value)
  end
  return tostring(value)
end

local function normalize_marker(value)
  return pandoc.text.lower(trim(value or "")):gsub("[^%w]+", "")
end

local skipped_header_classes = {
  nonrunning = true,
  unlisted = true,
  unnumbered = true,
  ["source-apparatus"] = true,
  ["source-titlepage"] = true,
  ["source-contents"] = true,
}

local function marker_is_nonrunning_type(marker)
  return marker == "toc"
    or marker == "content"
    or marker:match("contents") ~= nil
    or marker:match("titlepage") ~= nil
end

local function header_is_nonrunning(block)
  if block.classes then
    for _, class in ipairs(block.classes) do
      if skipped_header_classes[class] or skipped_header_classes[normalize_marker(class)] then
        return true
      end
    end
  end
  if block.attributes then
    for _, name in ipairs({ "data-type", "type" }) do
      local value = block.attributes[name]
      if value and marker_is_nonrunning_type(normalize_marker(value)) then
        return true
      end
    end
  end
  return false
end

local process_blocks

local function running_head_mark_for_header(block)
  local mark = shorten_text(pandoc.utils.stringify(block.content))
  if mark == "" then
    return nil
  end
  return pandoc.RawBlock("latex", "\\markright{" .. escape_tex(mark) .. "}")
end

process_blocks = function(blocks)
  local updated_blocks = pandoc.List()
  for _, block in ipairs(blocks) do
    if block.t == "Div" or block.t == "BlockQuote" then
      block.content = process_blocks(block.content)
      updated_blocks:insert(block)
    elseif block.t == "Header" then
      updated_blocks:insert(block)
      if not header_is_nonrunning(block) then
        local mark = running_head_mark_for_header(block)
        if mark then
          updated_blocks:insert(mark)
        end
      end
    else
      updated_blocks:insert(block)
    end
  end
  return updated_blocks
end

function Pandoc(doc)
  if not FORMAT:match("latex") then
    return nil
  end

  local updated_blocks = pandoc.List()
  local title = shorten_text(stringify_meta_value(doc.meta.title))
  if title ~= "" then
    updated_blocks:insert(pandoc.RawBlock("latex", "\\cmeSetRunningTitle{" .. escape_tex(title) .. "}"))
  end

  for _, block in ipairs(process_blocks(doc.blocks)) do
    updated_blocks:insert(block)
  end

  doc.blocks = updated_blocks
  return doc
end
