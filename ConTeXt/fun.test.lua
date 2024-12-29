require 'fun'

testarr = {"foo", "bar", "something : with subtitle", "something : with subtitle : and subsubtitle"}

print( apop({"somethin"}) )
local top, rest = apop ( testarr )
print("top: ", top )
print "rest:"
amap(
    rest,
    print
)

function varargs(...)
    amap({...}, print)
    print("len vargs: ",#arg)
    print("vargs: ",arg)
end
print("printing variable args")
varargs(1,2,3)
function addone(num)
    print("in addone: num: ", num)
    return num + 1
end
print(addone(1))
print("composed:", pipe(
    addone,
    print
    
) )
pipe(
    addone,
    print
)(1)

print('--- testing popthru')
print("result of popthru", popthru(print)(testarr) )

print('--- testing popthru in compose')
function customprint(...)
    print("in custom print: ", ...)
end

pipe(
    popthru(customprint),
    popthru(customprint),
    popthru(customprint)
)(testarr)


amap(reversetable(testarr), print)
