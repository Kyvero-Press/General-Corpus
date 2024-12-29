function identity(t)
    return t
end

function amap(t, fun)
    local newt = {}
    for k,v in pairs( t ) do
        fun( v, k )
    end
end

function onvalue (fun)
    return function(v,k)
        return fun(v)
    end
end


function valmap(t, fun)
    amap(t, onvalue(fun))
end

function copy(t)
    amap(t, identity)
end

function reversetable(tbl)
    local t = {}
    print("in reversetable: tbl: ", tbl)
    for k,v in pairs(tbl) do
        table.insert(t, 1, v)
    end
    return t
    
end


function apop(t)
    if( t == nil) then
        return
    end
    -- print ( #t )
    if ( #t ) <= 1 then
        return t[1]
    else
        return t[#t], { table.unpack(t, 1, #t-1) }
    end
end

-- do the thing on the top of the stack
-- return the rest of the stack
function popthru(fn)
    return function(tbl)
        if tbl == null then
            return
        end
        local top, stack = apop(tbl)
        fn(top)
        return stack
    end
end

function check_functions(...)
    for i,funp in ipairs( ... ) do
        if  type(funp) ~= "function" then
            error("param is not a function :: index: ", i)
        end
    end
    return ...
end

function pipe(...)
  local fnchain = check_functions {...}
  local function recurse(i, ...)
    if i == #fnchain then return fnchain[i](...) end
    return recurse(i + 1, fnchain[i](...))
  end
  return function(...) return recurse(1, ...) end
end
