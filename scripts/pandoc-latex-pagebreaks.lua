-- Pandoc Lua filter for CME LaTeX pagination.
--
-- The HTML converter marks verse stanzas/line groups as Divs with class "lg".
-- For LaTeX/PDF output, ask LaTeX not to begin one of those groups unless at
-- least a small stanza fragment can fit on the current page.  Also keep the
-- last few lines of each verse group together; this avoids the common Gawain
-- bob-and-wheel/sentence ending split across pages while still allowing long
-- stanzas to break earlier when necessary.

local min_stanza_fragment = "10\\baselineskip"
local protected_tail_lines = 5

local function has_class(el, class)
  for _, value in ipairs(el.classes) do
    if value == class then
      return true
    end
  end
  return false
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
  local inlines = {}
  for line_index, line in ipairs(lines) do
    if line_index > 1 then
      inlines[#inlines + 1] = pandoc.LineBreak()
    end
    for _, inline in ipairs(line) do
      inlines[#inlines + 1] = inline
    end
  end
  return inlines
end

local function with_protected_tail(block)
  if block.t ~= "Para" and block.t ~= "Plain" then
    return { block }
  end

  local lines = split_lines(block.content)
  if #lines <= protected_tail_lines then
    return { block }
  end

  local main_lines = {}
  local tail_lines = {}
  for index, line in ipairs(lines) do
    if index <= #lines - protected_tail_lines then
      main_lines[#main_lines + 1] = line
    else
      tail_lines[#tail_lines + 1] = line
    end
  end

  return {
    pandoc.Para(join_lines(main_lines)),
    pandoc.RawBlock("latex", "\\Needspace{" .. protected_tail_lines .. "\\baselineskip}\\vspace{-\\parskip}\\begin{samepage}"),
    pandoc.Para(join_lines(tail_lines)),
    pandoc.RawBlock("latex", "\\end{samepage}"),
  }
end

function Div(el)
  if FORMAT:match("latex") and has_class(el, "lg") then
    local blocks = { pandoc.RawBlock("latex", "\\Needspace{" .. min_stanza_fragment .. "}") }
    for _, block in ipairs(el.content) do
      for _, protected_block in ipairs(with_protected_tail(block)) do
        blocks[#blocks + 1] = protected_block
      end
    end
    return blocks
  end
end
