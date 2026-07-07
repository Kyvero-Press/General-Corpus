-- Pandoc Lua filter for CME LaTeX footnotes.
--
-- The HTML bridge represents source NOTE/NOTE1/etc. elements as spans with
-- class "note".  For LaTeX/PDF output, convert those spans in running text
-- into real Pandoc footnotes instead of leaving bracketed note text inline.

local note_class = "note"

local recursive_inline_types = {
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

local function inline_text(inline)
  return inline.text or inline.c or ""
end

local function set_inline_text(inline, text)
  inline.text = text
end

local function strip_leading_note_bracket(inlines)
  for _, inline in ipairs(inlines) do
    if inline.t == "Str" then
      local text = inline_text(inline)
      if text ~= "" then
        set_inline_text(inline, text:gsub("^%[", "", 1))
        return true
      end
    elseif recursive_inline_types[inline.t] and inline.content then
      if strip_leading_note_bracket(inline.content) then
        return true
      end
    elseif inline.t ~= "Space" and inline.t ~= "SoftBreak" and inline.t ~= "LineBreak" then
      return true
    end
  end
  return false
end

local function strip_trailing_note_bracket(inlines)
  for index = #inlines, 1, -1 do
    local inline = inlines[index]
    if inline.t == "Str" then
      local text = inline_text(inline)
      if text ~= "" then
        set_inline_text(inline, text:gsub("%]$", "", 1))
        return true
      end
    elseif recursive_inline_types[inline.t] and inline.content then
      if strip_trailing_note_bracket(inline.content) then
        return true
      end
    elseif inline.t ~= "Space" and inline.t ~= "SoftBreak" and inline.t ~= "LineBreak" then
      return true
    end
  end
  return false
end

local function remove_empty_top_level_strings(inlines)
  local cleaned = pandoc.List()
  for _, inline in ipairs(inlines) do
    if inline.t ~= "Str" or inline_text(inline) ~= "" then
      cleaned:insert(inline)
    end
  end
  return cleaned
end

local function note_content_from_span(span)
  local content = pandoc.List()
  for _, inline in ipairs(span.content or {}) do
    content:insert(inline)
  end
  strip_leading_note_bracket(content)
  strip_trailing_note_bracket(content)
  return remove_empty_top_level_strings(content)
end

local convert_notes

local function convert_inline(inline)
  if inline.t == "Span" and has_class(inline, note_class) then
    return pandoc.Note({ pandoc.Plain(note_content_from_span(inline)) })
  end

  if recursive_inline_types[inline.t] and inline.content then
    inline.content = convert_notes(inline.content)
  end
  return inline
end

convert_notes = function(inlines)
  local converted = pandoc.List()
  for _, inline in ipairs(inlines) do
    converted:insert(convert_inline(inline))
  end
  return converted
end

local function convert_inline_notes_in_block(block)
  if not FORMAT:match("latex") then
    return nil
  end
  block.content = convert_notes(block.content)
  return block
end

function Para(block)
  return convert_inline_notes_in_block(block)
end

function Plain(block)
  return convert_inline_notes_in_block(block)
end
