-- Pandoc Lua filter for CME LaTeX pagination.
--
-- The HTML converter marks verse stanzas/line groups as Divs with class "lg".
-- For LaTeX/PDF output, ask LaTeX not to begin one of those groups unless at
-- least a small fragment can fit on the current page.  Keep long verse groups
-- breakable, but protect high-risk clause continuations from page breaks.

local lg_start_needspace = "1\\baselineskip"
-- Keep clause protection local: longer runs recreate unbreakable verse chunks.
local max_consecutive_protected_breaks = 1

local continuation_words = {
  ["and"] = true,
  ["as"] = true,
  ["bot"] = true,
  ["but"] = true,
  ["for"] = true,
  ["in"] = true,
  ["of"] = true,
  ["that"] = true,
  ["to"] = true,
  ["with"] = true,
  ["þat"] = true,
}

local visible_container_inline_types = {
  Cite = true,
  Emph = true,
  Link = true,
  Quoted = true,
  SmallCaps = true,
  Span = true,
  Strikeout = true,
  Strong = true,
  Subscript = true,
  Superscript = true,
  Underline = true,
}

local function has_class(el, class)
  if not el.classes then
    return false
  end
  for _, value in ipairs(el.classes) do
    if value == class then
      return true
    end
  end
  return false
end

local function trim(text)
  return (text:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function inline_text(inline)
  return inline.text or inline.c or ""
end

local function is_latex_raw_inline(inline)
  return inline.t == "RawInline" and (inline.format == "latex" or inline.format == "tex")
end

local function is_verse_line_number_inline(inline)
  return is_latex_raw_inline(inline) and inline_text(inline):match("^\\cmeVerseLineNumber{") ~= nil
end

local function lettrine_visible_text(raw_latex)
  local initial, rest = raw_latex:match("^\\cmeLettrine{([^}]*)}{([^}]*)}")
  if initial then
    return initial .. rest
  end
  return ""
end

local inlines_visible_text

local function inline_visible_text(inline)
  if is_verse_line_number_inline(inline) then
    return ""
  end
  if inline.t == "Str" or inline.t == "Code" then
    return inline_text(inline)
  end
  if inline.t == "Space" or inline.t == "SoftBreak" or inline.t == "LineBreak" then
    return " "
  end
  if is_latex_raw_inline(inline) then
    return lettrine_visible_text(inline_text(inline))
  end
  if visible_container_inline_types[inline.t] and inline.content then
    return inlines_visible_text(inline.content)
  end
  return ""
end

inlines_visible_text = function(inlines)
  local parts = {}
  for _, inline in ipairs(inlines) do
    parts[#parts + 1] = inline_visible_text(inline)
  end
  return table.concat(parts)
end

local function word_count(text)
  local count = 0
  for _ in text:gmatch("%S+") do
    count = count + 1
  end
  return count
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

local function strip_closing_punctuation(text)
  return trim(text):gsub("[%s\"'”’%)%]]+$", "")
end

local function previous_line_allows_protected_break(text)
  local stripped = strip_closing_punctuation(text)
  if stripped == "" then
    return false
  end
  return stripped:match("[%.%!%?%;%:]$") == nil
end

local function starts_with_lowercase(text)
  local ok, result = pcall(function()
    for _, codepoint in utf8.codes(text) do
      local character = utf8.char(codepoint)
      if character:match("%s") or character:match("%p") then
        -- Skip leading whitespace and ASCII punctuation/quotes.
      else
        return pandoc.text.lower(character) == character and pandoc.text.upper(character) ~= character
      end
    end
    return false
  end)
  if ok then
    return result
  end

  -- Some recovered corpus XML reaches Pandoc as byte strings that are not
  -- valid UTF-8.  Clause-protection is only a pagination hint, so prefer a
  -- conservative unprotected line break over failing the entire PDF build.
  return false
end

local function next_line_is_short_continuation(text)
  local stripped = trim(text):gsub("^[\"'“‘%(%[]+", "")
  if stripped == "" then
    return false
  end

  local lower_text = pandoc.text.lower(stripped)
  local first_word = lower_text:match("^([^%s%p]+)") or ""
  local short_enough = word_count(stripped) <= 4 or utf8_length(stripped) <= 40

  return short_enough and (continuation_words[first_word] or starts_with_lowercase(stripped))
end

local function should_protect_break(previous_line, next_line)
  return previous_line_allows_protected_break(inlines_visible_text(previous_line))
    and next_line_is_short_continuation(inlines_visible_text(next_line))
end

local function split_lines(inlines)
  local lines = { {} }
  for _, inline in ipairs(inlines) do
    if inline.t == "LineBreak" then
      lines[#lines + 1] = {}
    else
      lines[#lines][#lines[#lines] + 1] = inline
    end
  end
  return lines
end

local function join_lines(lines)
  local inlines = pandoc.List()
  local consecutive_protected_breaks = 0

  for line_index, line in ipairs(lines) do
    if line_index > 1 then
      if should_protect_break(lines[line_index - 1], line)
        and consecutive_protected_breaks < max_consecutive_protected_breaks then
        inlines:insert(pandoc.RawInline("latex", "\\\\*"))
        consecutive_protected_breaks = consecutive_protected_breaks + 1
      else
        inlines:insert(pandoc.LineBreak())
        consecutive_protected_breaks = 0
      end
    end
    for _, inline in ipairs(line) do
      inlines:insert(inline)
    end
  end
  return inlines
end

local function with_clause_protection(block)
  if block.t ~= "Para" and block.t ~= "Plain" then
    return block
  end

  block.content = join_lines(split_lines(block.content))
  return block
end

function Div(el)
  if FORMAT:match("latex") and has_class(el, "lg") then
    local blocks = { pandoc.RawBlock("latex", "\\Needspace{" .. lg_start_needspace .. "}") }
    for _, block in ipairs(el.content) do
      blocks[#blocks + 1] = with_clause_protection(block)
    end
    return blocks
  end
end
