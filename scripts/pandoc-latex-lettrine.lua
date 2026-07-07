-- Pandoc Lua filter for CME LaTeX lettrines.
--
-- For LaTeX/PDF output, replace the first visible word after the document
-- start and after each heading with \cmeLettrine{initial}{rest}.  The actual
-- lettrine style is selected by scripts/pandoc-cme-xml through LaTeX headers;
-- this filter only marks the initial word.

local skipped_container_classes = {
  titlepage = true,
  ["source-metadata"] = true,
  apparatus = true,
  ["provenance-note"] = true,
  ["transcription-note"] = true,
  ["editorial-note"] = true,
  headwords = true,
  headnote = true,
  argument = true,
  epigraph = true,
  opener = true,
  byline = true,
  dateline = true,
  closer = true,
  signed = true,
  salute = true,
  trailer = true,
  lg = true,
  l = true,
  ["verse-lines"] = true,
  lineated = true,
  verse = true,
  speech = true,
  speaker = true,
  stage = true,
  direction = true,
  table = true,
}

local pending_consuming_container_classes = {
  lg = true,
  l = true,
  ["verse-lines"] = true,
  lineated = true,
  verse = true,
  speech = true,
  speaker = true,
  stage = true,
  direction = true,
  table = true,
}

local skipped_inline_classes = {
  bibl = true,
  note = true,
  headnote = true,
  argument = true,
  epigraph = true,
}

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

local function has_class_in(el, class_set)
  if not el.classes then
    return false
  end
  for _, class in ipairs(el.classes) do
    if class_set[class] then
      return true
    end
  end
  return false
end

local function has_skipped_class(el)
  return has_class_in(el, skipped_container_classes)
end

local function consumes_pending_dropcap(el)
  return has_class_in(el, pending_consuming_container_classes)
end

local function is_skipped_inline(inline)
  return inline.t == "Span" and has_class_in(inline, skipped_inline_classes)
end

local function inline_text(inline)
  return inline.text or inline.c or ""
end

local function is_combining_mark(codepoint)
  return (codepoint >= 0x0300 and codepoint <= 0x036F)
    or (codepoint >= 0x1AB0 and codepoint <= 0x1AFF)
    or (codepoint >= 0x1DC0 and codepoint <= 0x1DFF)
    or (codepoint >= 0x20D0 and codepoint <= 0x20FF)
    or (codepoint >= 0xFE20 and codepoint <= 0xFE2F)
end

local function is_alphabetic_codepoint(codepoint)
  local character = utf8.char(codepoint)
  return pandoc.text.lower(character) ~= pandoc.text.upper(character)
end

local function split_at_first_letter_cluster(text)
  local characters = {}
  for position, codepoint in utf8.codes(text) do
    characters[#characters + 1] = { position = position, codepoint = codepoint }
  end

  for index, character in ipairs(characters) do
    if is_alphabetic_codepoint(character.codepoint) then
      local cluster_end = characters[index + 1] and (characters[index + 1].position - 1) or #text
      local mark_index = index + 1
      while characters[mark_index] and is_combining_mark(characters[mark_index].codepoint) do
        cluster_end = characters[mark_index + 1] and (characters[mark_index + 1].position - 1) or #text
        mark_index = mark_index + 1
      end

      return {
        prefix = text:sub(1, character.position - 1),
        initial = text:sub(character.position, cluster_end),
        rest = text:sub(cluster_end + 1),
      }
    end
  end

  return nil
end

local function lettrine_replacement(text)
  local split = split_at_first_letter_cluster(text)
  if not split then
    return nil
  end

  local replacement = pandoc.List()
  if split.prefix ~= "" then
    replacement:insert(pandoc.Str(split.prefix))
  end
  replacement:insert(pandoc.RawInline(
    "latex",
    "\\cmeLettrine{" .. escape_tex(split.initial) .. "}{" .. escape_tex(split.rest) .. "}"
  ))
  return replacement
end

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
}

local plain_text_inline_types = {
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

local function single_inline_list(inline)
  local result = pandoc.List()
  result:insert(inline)
  return result
end

local mark_inline

local function mark_inlines(inlines)
  local updated = pandoc.List()
  for index, inline in ipairs(inlines) do
    local replacement, marked = mark_inline(inline)
    if marked then
      for _, replacement_inline in ipairs(replacement) do
        updated:insert(replacement_inline)
      end
      for remaining = index + 1, #inlines do
        updated:insert(inlines[remaining])
      end
      return updated, true
    end
    updated:insert(inline)
  end
  return inlines, false
end

mark_inline = function(inline)
  if is_skipped_inline(inline) then
    return nil, false
  end

  if inline.t == "Str" then
    local replacement = lettrine_replacement(inline_text(inline))
    if replacement then
      return replacement, true
    end
    return nil, false
  end

  if recursive_inline_types[inline.t] and inline.content then
    local content, marked = mark_inlines(inline.content)
    if marked then
      inline.content = content
      return single_inline_list(inline), true
    end
  end

  return nil, false
end

local function trim(text)
  return (text:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function inlines_plain_text(inlines)
  local parts = {}
  for _, inline in ipairs(inlines) do
    if is_skipped_inline(inline) then
      -- Editorial/source notes should not be considered reading text for
      -- drop-cap placement.  If prose follows the note in the same paragraph,
      -- it remains eligible.
    elseif inline.t == "Str" or inline.t == "Code" then
      parts[#parts + 1] = inline_text(inline)
    elseif inline.t == "Space" or inline.t == "SoftBreak" or inline.t == "LineBreak" then
      parts[#parts + 1] = " "
    elseif plain_text_inline_types[inline.t] and inline.content then
      parts[#parts + 1] = inlines_plain_text(inline.content)
    end
  end
  return table.concat(parts)
end

local function inline_has_visible_text(inline)
  if is_skipped_inline(inline) then
    return false
  end
  if inline.t == "Str" or inline.t == "Code" then
    return trim(inline_text(inline)) ~= ""
  end
  if inline.t == "Space" or inline.t == "SoftBreak" or inline.t == "LineBreak" then
    return false
  end
  if plain_text_inline_types[inline.t] and inline.content then
    return trim(inlines_plain_text(inline.content)) ~= ""
  end
  return false
end

local function first_visible_inline(inlines)
  for _, inline in ipairs(inlines) do
    if inline_has_visible_text(inline) then
      return inline
    end
  end
  return nil
end

local function first_visible_inline_deep(inlines)
  local first_inline = first_visible_inline(inlines)
  if not first_inline then
    return nil
  end

  if first_inline.t == "Underline" or first_inline.t == "Emph" or first_inline.t == "Strong" then
    return first_inline
  end

  if plain_text_inline_types[first_inline.t] and first_inline.content then
    return first_visible_inline_deep(first_inline.content) or first_inline
  end

  return first_inline
end

local function has_terminal_label_punctuation(text)
  local label = trim(text):gsub("[\"'”’%)%]]+$", "")
  return label:match("[%.%!%?%:%;]$") ~= nil
end

local function word_count(text)
  local count = 0
  for _ in text:gmatch("%S+") do
    count = count + 1
  end
  return count
end

local function bracket_segment_is_note_like(content, doubled)
  if doubled then
    return true
  end

  local normalized = trim(pandoc.text.lower(content))
  if normalized:match("^%a%]?$") then
    return false
  end

  return normalized:match("margin") ~= nil
    or normalized:match("editor") ~= nil
    or normalized:match("will%s+made") ~= nil
    or normalized:match("^st%.") ~= nil
    or (
      #normalized >= 8
      and normalized:match("%s") ~= nil
      and (
        normalized:match("[%.%!%?%:%;]$") ~= nil
        or normalized:match(",") ~= nil
      )
    )
end

local function leading_bracketed_segment(text)
  local trimmed = trim(text)
  local doubled_content, doubled_rest = trimmed:match("^%[%[(.*)%]%](.*)$")
  if doubled_content then
    return doubled_content, doubled_rest, true
  end

  local content, rest = trimmed:match("^%[([^%]]*)%](.*)$")
  if content then
    return content, rest, false
  end

  return nil, nil, false
end

local function remaining_text_is_note_only(text)
  local remaining = trim(text):gsub("^%]+", "")
  while remaining ~= "" do
    local content, rest, doubled = leading_bracketed_segment(remaining)
    if content and bracket_segment_is_note_like(content, doubled) then
      remaining = trim(rest):gsub("^%]+", "")
    else
      local citation, citation_rest = remaining:match("^(%b())(.*)$")
      if not citation then
        return false
      end
      remaining = trim(citation_rest):gsub("^%]+", "")
    end
  end
  return true
end

local lower_trimmed
local is_body_opening

local function begins_with_bracketed_note_label(text)
  local content, rest, doubled = leading_bracketed_segment(text)
  if not content or not bracket_segment_is_note_like(content, doubled) then
    return false
  end

  local normalized = lower_trimmed(content)
  local rest_text = lower_trimmed(rest)
  if doubled or normalized:match("margin") or normalized:match("editor") then
    return not is_body_opening(rest_text)
  end

  return remaining_text_is_note_only(rest)
end

local function begins_with_underlined_label(inlines)
  local first_inline = first_visible_inline_deep(inlines)
  if not first_inline or first_inline.t ~= "Underline" then
    return false
  end
  return has_terminal_label_punctuation(inlines_plain_text(first_inline.content))
end

function lower_trimmed(text)
  return trim(pandoc.text.lower(text))
end

local function matches_any(text, patterns)
  for _, pattern in ipairs(patterns) do
    if text:match(pattern) then
      return true
    end
  end
  return false
end

local body_opening_patterns = {
  "^in%s+dei%s+nomine",
  "^in%s+the%s+name%s+of%s+god",
}

local emphasized_label_patterns = {
  "^testamentum%s",
  "^testamentum$",
  "^probatum%s",
  "^probatum$",
  "^probate%s",
  "^probate$",
  "^codicil",
  "^the%s+codicil",
  "^will%s+made",
  "^in%s+margin",
  "^margin",
  "^nota%s",
  "^nota$",
  "^memorandum%s",
  "^memorandum$",
  "^tenor%s+vero",
  "^tenor$",
}

function is_body_opening(text)
  return matches_any(lower_trimmed(text), body_opening_patterns)
end

local function is_known_emphasized_label(text)
  return matches_any(lower_trimmed(text), emphasized_label_patterns)
end

local function text_after_prefix(text, prefix)
  local trimmed_text = trim(text)
  local trimmed_prefix = trim(prefix)
  if trimmed_text:sub(1, #trimmed_prefix) == trimmed_prefix then
    return trimmed_text:sub(#trimmed_prefix + 1)
  end
  return ""
end

local function begins_with_emphasized_label(inlines)
  local first_inline = first_visible_inline_deep(inlines)
  if not first_inline or (first_inline.t ~= "Emph" and first_inline.t ~= "Strong") then
    return false
  end

  local emphasized_text = inlines_plain_text(first_inline.content)
  local paragraph_text = inlines_plain_text(inlines)
  if is_body_opening(emphasized_text) or is_body_opening(paragraph_text) then
    return false
  end

  local rest = text_after_prefix(paragraph_text, emphasized_text)
  local whole_paragraph_is_emphasis = trim(rest) == ""
  local rest_is_note_only = remaining_text_is_note_only(rest)
  local paragraph_is_short = word_count(paragraph_text) <= 18
  local paragraph_has_label_punctuation = has_terminal_label_punctuation(paragraph_text)

  if is_known_emphasized_label(emphasized_text)
      and (whole_paragraph_is_emphasis or rest_is_note_only)
      and (paragraph_is_short or paragraph_has_label_punctuation) then
    return true
  end

  if lower_trimmed(emphasized_text):match("testamentum")
      and (whole_paragraph_is_emphasis or rest_is_note_only)
      and paragraph_is_short then
    return true
  end

  return false
end

local function is_short_margin_or_editorial_label(text)
  local lower_text = lower_trimmed(text)
  if lower_text == "" or is_body_opening(lower_text) then
    return false
  end

  local marker_start = lower_text:find("in margin", 1, true) or lower_text:find("editor", 1, true)
  if not marker_start then
    return false
  end

  -- Source labels often appear as short testament/register captions followed by
  -- an "In margin" note.  Do not skip long prose paragraphs merely because a
  -- margin note appears later in the running text.
  if word_count(lower_text) <= 28 then
    return true
  end

  local before_marker = trim(lower_text:sub(1, marker_start - 1))
  return marker_start <= 180 and has_terminal_label_punctuation(before_marker)
end

local function is_short_plain_or_mixed_label(text)
  local lower_text = lower_trimmed(text)
  if lower_text == "" or is_body_opening(lower_text) then
    return false
  end
  return word_count(lower_text) <= 14
    and (
      lower_text:match("testamentum") ~= nil
      or lower_text:match("codicil") ~= nil
      or lower_text:match("probatum") ~= nil
    )
end

local function should_skip_dropcap_paragraph(block)
  local text = inlines_plain_text(block.content)
  return begins_with_bracketed_note_label(text)
    or is_short_margin_or_editorial_label(text)
    or begins_with_underlined_label(block.content)
    or begins_with_emphasized_label(block.content)
    or is_short_plain_or_mixed_label(text)
end

local function mark_first_word(block)
  if should_skip_dropcap_paragraph(block) then
    return false
  end

  local content, marked = mark_inlines(block.content)
  if marked then
    block.content = content
  end
  return marked
end

local function can_receive_dropcap(block)
  return (block.t == "Para" or block.t == "Plain")
    and not should_skip_dropcap_paragraph(block)
    and first_visible_inline(block.content) ~= nil
end

local function is_running_head_mark(block)
  return block.t == "RawBlock"
    and block.format == "latex"
    and block.text:match("^\\markright{") ~= nil
end

local function next_block_receives_dropcap(blocks, start_index)
  for index = start_index + 1, #blocks do
    local next_block = blocks[index]
    if is_running_head_mark(next_block) then
      -- The running-head filter inserts \markright immediately after headings;
      -- it should not break the heading/opening-paragraph keep-with-next check.
    elseif can_receive_dropcap(next_block) then
      return true
    else
      return false
    end
  end
  return false
end

function Pandoc(doc)
  if not FORMAT:match("latex") then
    return nil
  end

  local pending_dropcap = true
  local section_opening_space_reserved = false

  local function process_blocks(blocks)
    local processed = pandoc.List()
    for index, block in ipairs(blocks) do
      if block.t == "Header" then
        pending_dropcap = true
        section_opening_space_reserved = next_block_receives_dropcap(blocks, index)
        if section_opening_space_reserved then
          processed:insert(pandoc.RawBlock("latex", "\\Needspace{20\\baselineskip}%"))
        end
        processed:insert(block)
      elseif block.t == "Div" then
        if has_skipped_class(block) then
          if pending_dropcap and consumes_pending_dropcap(block) then
            pending_dropcap = false
            section_opening_space_reserved = false
          end
          processed:insert(block)
        else
          block.content = process_blocks(block.content)
          processed:insert(block)
        end
      elseif pending_dropcap and block.t == "LineBlock" then
        pending_dropcap = false
        section_opening_space_reserved = false
        processed:insert(block)
      elseif pending_dropcap and (block.t == "Para" or block.t == "Plain") then
        if can_receive_dropcap(block) then
          processed:insert(pandoc.RawBlock("latex", "\\Needspace{6\\baselineskip}%"))
        end
        if mark_first_word(block) then
          pending_dropcap = false
          section_opening_space_reserved = false
        end
        processed:insert(block)
      else
        processed:insert(block)
      end
    end
    return processed
  end

  doc.blocks = process_blocks(doc.blocks)
  return doc
end
