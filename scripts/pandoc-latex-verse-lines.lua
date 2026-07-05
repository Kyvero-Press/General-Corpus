-- Pandoc Lua filter for CME LaTeX verse line numbers.
--
-- For LaTeX/PDF output, insert a small margin number before every fifth
-- visible verse line.  Source line numbers from the HTML converter are used
-- when present; otherwise a running fallback counter is used.

traverse = "topdown"

local fallback_line_number = 0
local handled_attr = "verse-lines-handled"
-- Match pandoc-latex-lettrine.tex's \lettrine[lines=3] box: do not
-- place margin verse numbers on the drop-cap line or the next two lines.
local lettrine_suppressed_lines = 3

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

local function safe_numeric(value)
  if type(value) ~= "string" then
    return nil
  end
  local digits = value:match("^%s*(%d+)%s*$")
  if not digits then
    return nil
  end
  local number = tonumber(digits)
  if not number or number <= 0 then
    return nil
  end
  return number
end

local function source_number_from_attrs(el)
  if not el.attributes then
    return nil
  end
  return safe_numeric(el.attributes["line-number"]) or safe_numeric(el.attributes.n)
end

local function source_number_from_verse_span(inline)
  if inline.t == "Span" and has_class(inline, "verse-line") and inline.attributes then
    return safe_numeric(inline.attributes["line-number"])
  end
  if inline.content then
    for _, child in ipairs(inline.content) do
      local number = source_number_from_verse_span(child)
      if number then
        return number
      end
    end
  end
  return nil
end

local function line_source_number(line)
  for _, inline in ipairs(line) do
    local number = source_number_from_verse_span(inline)
    if number then
      return number
    end
  end
  return nil
end

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

local function inline_has_content(inline)
  if inline.t == "Str" or inline.t == "Code" or inline.t == "RawInline" then
    return trim(inline_text(inline)) ~= ""
  end
  if inline.t == "Space" or inline.t == "SoftBreak" or inline.t == "LineBreak" then
    return false
  end
  if visible_container_inline_types[inline.t] and inline.content then
    for _, child in ipairs(inline.content) do
      if inline_has_content(child) then
        return true
      end
    end
    return false
  end
  return true
end

local function line_has_content(line)
  for _, inline in ipairs(line) do
    if inline_has_content(inline) then
      return true
    end
  end
  return false
end

local function block_has_content(block)
  if block.t == "Para" or block.t == "Plain" then
    return line_has_content(block.content)
  end
  return true
end

local function div_has_content(el)
  for _, block in ipairs(el.content) do
    if block_has_content(block) then
      return true
    end
  end
  return false
end

local function split_lines(inlines)
  local lines = { pandoc.List() }
  for _, inline in ipairs(inlines) do
    if inline.t == "LineBreak" then
      lines[#lines + 1] = pandoc.List()
    else
      lines[#lines]:insert(inline)
    end
  end
  return lines
end

local function join_lines(lines)
  local inlines = pandoc.List()
  for line_index, line in ipairs(lines) do
    if line_index > 1 then
      inlines:insert(pandoc.LineBreak())
    end
    for _, inline in ipairs(line) do
      inlines:insert(inline)
    end
  end
  return inlines
end

local function verse_line_number_inline(number)
  return pandoc.RawInline("latex", "\\cmeVerseLineNumber{" .. tostring(number) .. "}")
end

local function is_latex_raw_inline(inline)
  return inline.t == "RawInline" and (inline.format == "latex" or inline.format == "tex")
end

local function is_cme_lettrine_inline(inline)
  return is_latex_raw_inline(inline) and inline_text(inline):match("^\\cmeLettrine") ~= nil
end

local function has_existing_verse_line_number(line)
  for _, inline in ipairs(line) do
    if is_latex_raw_inline(inline)
      and inline_text(inline):match("^\\cmeVerseLineNumber{") then
      return true
    end
    if inline.t ~= "Space" and inline.t ~= "SoftBreak" then
      return false
    end
  end
  return false
end

local function first_meaningful_inline_starts_with_lettrine(inlines)
  for _, inline in ipairs(inlines) do
    if inline.t == "Space" or inline.t == "SoftBreak" then
      -- Whitespace does not affect whether a lettrine starts the visible line.
    elseif is_cme_lettrine_inline(inline) then
      return true
    elseif visible_container_inline_types[inline.t] and inline.content then
      local nested = first_meaningful_inline_starts_with_lettrine(inline.content)
      if nested ~= nil then
        return nested
      end
    elseif inline_has_content(inline) then
      return false
    end
  end
  return nil
end

local function line_starts_with_lettrine(line)
  return first_meaningful_inline_starts_with_lettrine(line) == true
end

local function lettrine_suppression_for_visible_line(line, suppression_remaining)
  suppression_remaining = suppression_remaining or 0
  if line_starts_with_lettrine(line) then
    suppression_remaining = lettrine_suppressed_lines
  end
  local suppress_number = suppression_remaining > 0
  if suppression_remaining > 0 then
    suppression_remaining = suppression_remaining - 1
  end
  return suppress_number, suppression_remaining
end

local function prepend_number_to_line(line, number)
  if has_existing_verse_line_number(line) or line_starts_with_lettrine(line) then
    return line
  end
  local updated = pandoc.List()
  updated:insert(verse_line_number_inline(number))
  for _, inline in ipairs(line) do
    updated:insert(inline)
  end
  return updated
end

local function line_number_to_insert_for_source(source_number)
  if source_number and source_number % 5 == 0 then
    return source_number
  end
  return nil
end

local function line_number_to_insert_for_fallback()
  fallback_line_number = fallback_line_number + 1
  if fallback_line_number % 5 == 0 then
    return fallback_line_number
  end
  return nil
end

local function lg_has_source_numbers(blocks)
  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      for _, line in ipairs(split_lines(block.content)) do
        if line_source_number(line) then
          return true
        end
      end
    elseif block.t == "Div" and has_class(block, "l") and source_number_from_attrs(block) then
      return true
    end
  end
  return false
end

local function process_lg_inline_block(block, use_source_numbers, lettrine_suppression_remaining)
  if block.t ~= "Para" and block.t ~= "Plain" then
    return block, lettrine_suppression_remaining or 0
  end

  lettrine_suppression_remaining = lettrine_suppression_remaining or 0
  local updated_lines = {}
  for _, line in ipairs(split_lines(block.content)) do
    local number_to_insert = nil
    if line_has_content(line) then
      if use_source_numbers then
        number_to_insert = line_number_to_insert_for_source(line_source_number(line))
      else
        number_to_insert = line_number_to_insert_for_fallback()
      end
      local suppress_number
      suppress_number, lettrine_suppression_remaining = lettrine_suppression_for_visible_line(
        line,
        lettrine_suppression_remaining
      )
      if suppress_number then
        number_to_insert = nil
      end
    end
    if number_to_insert then
      updated_lines[#updated_lines + 1] = prepend_number_to_line(line, number_to_insert)
    else
      updated_lines[#updated_lines + 1] = line
    end
  end

  block.content = join_lines(updated_lines)
  return block, lettrine_suppression_remaining
end

local function prepend_number_to_first_inline_block(blocks, number)
  for index, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      block.content = prepend_number_to_line(block.content, number)
      blocks[index] = block
      return true
    end
  end
  return false
end

local function first_content_inline_block_line(blocks)
  for _, block in ipairs(blocks) do
    if (block.t == "Para" or block.t == "Plain") and line_has_content(block.content) then
      return block.content
    end
  end
  return nil
end

local function mark_handled(el)
  el.attributes = el.attributes or {}
  el.attributes[handled_attr] = "1"
  return el
end

local function clear_handled(el)
  if el.attributes then
    el.attributes[handled_attr] = nil
  end
  return el
end

local function process_l_div(el, use_source_numbers, suppress_number)
  if not div_has_content(el) then
    return nil
  end

  local source_number = source_number_from_attrs(el)
  local number_to_insert = nil
  if source_number then
    number_to_insert = line_number_to_insert_for_source(source_number)
  elseif not use_source_numbers then
    number_to_insert = line_number_to_insert_for_fallback()
  end
  if suppress_number then
    number_to_insert = nil
  end

  if number_to_insert and prepend_number_to_first_inline_block(el.content, number_to_insert) then
    return el
  end
  return nil
end

local function process_lg_div(el)
  local use_source_numbers = lg_has_source_numbers(el.content)
  local lettrine_suppression_remaining = 0
  for index, block in ipairs(el.content) do
    if block.t == "Para" or block.t == "Plain" then
      local processed_block
      processed_block, lettrine_suppression_remaining = process_lg_inline_block(
        block,
        use_source_numbers,
        lettrine_suppression_remaining
      )
      el.content[index] = processed_block
    elseif block.t == "Div" and has_class(block, "l") then
      local suppress_number = false
      local first_line = first_content_inline_block_line(block.content)
      if first_line then
        suppress_number, lettrine_suppression_remaining = lettrine_suppression_for_visible_line(
          first_line,
          lettrine_suppression_remaining
        )
      end
      process_l_div(block, use_source_numbers, suppress_number)
      el.content[index] = mark_handled(block)
    end
  end
  return el
end

function Div(el)
  if not FORMAT:match("latex") then
    return nil
  end
  if el.attributes and el.attributes[handled_attr] then
    return clear_handled(el)
  end
  if has_class(el, "lg") then
    return process_lg_div(el)
  end
  if has_class(el, "l") then
    return process_l_div(el, false, false)
  end
  return nil
end
