require 'fun'
function trim1(s)
   return (s:gsub("^%s*(.-)%s*$", "%1"))
end
function spliton(str, sep)
    if sep == nil then
        sep = "%s"
    end
    local t = {}
    for sub in string.gmatch(str, "([^"..sep.."]*)") do
        print("inserting::sub ", sub)
        table.insert(t,trim1( sub ))
    end
    return t
end

function splitname(name)

    return spliton(name, ":")
end

function removeparasymbol(str)
    return str:gsub("¶", "")
end

function processtitle(str, setvar)
    return pipe(
        splitname,
        popthru(setvar("title")),
        popthru(setvar("subtitle")),
        popthru(setvar("subsubtitle"))
    )(str)
end

