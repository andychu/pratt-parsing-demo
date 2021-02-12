#!/usr/bin/python3
import tdop
import arith_parse


def _assert_parse_error(s: str, error_substring: str = "") -> None:
    try:
        node = tdop.parse(arith_parse.rule_map, tdop.TokenStream(s))
    except tdop.ParseError as e:
        err = str(e)
        if error_substring in err:
            print("got expected error for %s: %s" % (s, err))
        else:
            raise AssertionError("Expected %r to be in %r" % (error_substring, err))
    else:
        raise AssertionError("%r should have failed" % s)


def _assert_parse(s: str, expected: str) -> None:
    """Used by tests."""
    tree = tdop.parse(arith_parse.rule_map, tdop.TokenStream(s))

    sexpr = repr(tree)
    if expected is not None:
        assert sexpr == expected, "%r != %r" % (sexpr, expected)

    print("%-40s %s" % (s, sexpr))


def TestArith() -> None:
    _assert_parse("1+2+3", "(+ (+ 1 2) 3)")
    _assert_parse("1+2*3", "(+ 1 (* 2 3))")
    _assert_parse("4*(2+3)", "(* 4 (+ 2 3))")
    _assert_parse("(2+3)*4", "(* (+ 2 3) 4)")
    _assert_parse("1<2", "(< 1 2)")
    _assert_parse("x=3", "(= x 3)")
    _assert_parse("x = 2*3", "(= x (* 2 3))")
    _assert_parse("x = y", "(= x y)")

    _assert_parse("x*y - y*z", "(- (* x y) (* y z))")
    _assert_parse("x/y - y%z", "(- (/ x y) (% y z))")

    _assert_parse("x = y", "(= x y)")
    _assert_parse("2 ** 3 ** 2", "(** 2 (** 3 2))")
    _assert_parse("- 3 ** 2", "(- (** 3 2))")
    _assert_parse("a = b = 10", "(= a (= b 10))")

    _assert_parse("x = ((y*4)-2)", "(= x (- (* y 4) 2))")

    _assert_parse("x - -y", "(- x (- y))")
    _assert_parse("-1 * -2", "(* (- 1) (- 2))")
    _assert_parse("-x * -y", "(* (- x) (- y))")
    _assert_parse("x - -234", "(- x (- 234))")

    # Python doesn't allow this
    _assert_parse("x += y += 3", "(+= x (+= y 3))")

    # This is sort of nonsensical, but bash allows it.  The 1 is discarded as
    # the first element of the comma operator.
    _assert_parse("x[1,2]", "(get x (, 1 2))")

    # Python doesn't have unary +
    _assert_parse("+1 - +2", "(- (+ 1) (+ 2))")

    # LHS
    _assert_parse("f[x] += 1", "(+= (get f x) 1)")


def TestBitwise() -> None:
    _assert_parse("~1 | ~2", "(| (~ 1) (~ 2))")
    _assert_parse("x & y | a & b", "(| (& x y) (& a b))")
    _assert_parse("~x ^ y", "(^ (~ x) y)")
    _assert_parse("x << y | y << z", "(| (<< x y) (<< y z))")

    _assert_parse("a ^= b-1", "(^= a (- b 1))")


def TestLogical() -> None:
    _assert_parse("a && b || c && d", "(|| (&& a b) (&& c d))")
    _assert_parse("!a && !b", "(&& (! a) (! b))")
    _assert_parse("a != b && c == d", "(&& (!= a b) (== c d))")

    _assert_parse("a > b ? 0 : 1", "(? (> a b) 0 1)")
    _assert_parse("a > b ? x+1 : y+1", "(? (> a b) (+ x 1) (+ y 1))")

    _assert_parse("1 ? true1 : 2 ? true2 : false", "(? 1 true1 (? 2 true2 false))")
    _assert_parse("1 ? true1 : (2 ? true2 : false)", "(? 1 true1 (? 2 true2 false))")

    _assert_parse("1 ? (2 ? true : false1) : false2", "(? 1 (? 2 true false1) false2)")
    _assert_parse("1 ? 2 ? true : false1 : false2", "(? 1 (? 2 true false1) false2)")

    # [cling]$ true ? 1 : 2, true ? 3 : 4
    # (int) 3
    # Comma expressions can be inside
    _assert_parse("x ? 1 : 2, y ? 3 : 4", "(, (? x 1 2) (? y 3 4))")
    _assert_parse("a , b ? c, d : e, f", "(, a (? b (, c d) e) f)")


def TestUnary() -> None:
    _assert_parse("!x", "(! x)")
    _assert_parse("x--", "(post-- x)")
    _assert_parse("x[1]--", "(post-- (get x 1))")

    _assert_parse("--x", "(-- x)")
    _assert_parse("++x[1]", "(++ (get x 1))")

    _assert_parse("!x--", "(! (post-- x))")
    _assert_parse("~x++", "(~ (post++ x))")

    _assert_parse("x++ - y++", "(- (post++ x) (post++ y))")

    _assert_parse("++x - ++y", "(- (++ x) (++ y))")

    #
    # 1.   x++  f()  x[]  left associative
    #                     f(x)[1]++  means
    #                     (++ (get (call f x) 1))
    # 2.   ++x  + - ! ~   right associative
    #                     -++x means (- (++ x))


def TestArrays() -> None:
    """Shared between shell, oil, and Python."""
    _assert_parse("x[1]", "(get x 1)")
    _assert_parse("x[a+b]", "(get x (+ a b))")


def TestComma() -> None:
    _assert_parse("x=1,y=2,z=3", "(, (= x 1) (= y 2) (= z 3))")


def TestFuncCalls() -> None:
    _assert_parse("x = y(2)*3 + y(4)*5", "(= x (+ (* (call y 2) 3) (* (call y 4) 5)))")

    _assert_parse("x(1,2)+y(3,4)", "(+ (call x 1 2) (call y 3 4))")
    _assert_parse("x(a,b,c[d])", "(call x a b (get c d))")
    _assert_parse(
        "x(1,2)*j+y(3,4)*k+z(5,6)*l",
        "(+ (+ (* (call x 1 2) j) (* (call y 3 4) k)) (* (call z 5 6) l))",
    )
    _assert_parse("print(test(2,3))", "(call print (call test 2 3))")
    _assert_parse('print("x")', "(call print x)")
    _assert_parse("min(255,n*2)", "(call min 255 (* n 2))")
    _assert_parse("c = pal[i*8]", "(= c (get pal (* i 8)))")


def TestErrors() -> None:
    _assert_parse_error("}")
    _assert_parse_error("]")

    _assert_parse_error("{")  # depends on language

    _assert_parse_error("x+1 = y", "Can't assign")
    _assert_parse_error("(x+1)++", "Can't assign")

    # Should be an EOF error
    _assert_parse_error("foo ? 1 :", "Unexpected end")

    _assert_parse_error("foo ? 1 ", "expected :")
    _assert_parse_error("%", "can't be used in prefix position")

    error_str = "can't be used in prefix"
    _assert_parse_error("}")
    _assert_parse_error("{")
    _assert_parse_error("]", error_str)

    _assert_parse_error("1 ( 2", "can't be called")
    _assert_parse_error("(x+1) ( 2 )", "can't be called")
    # _assert_parse_error('1 ) 2')

    _assert_parse_error("1 [ 2 ]", "can't be indexed")


def main() -> None:
    TestArith()
    TestBitwise()
    TestLogical()
    TestUnary()
    TestArrays()
    TestFuncCalls()
    TestComma()
    TestErrors()


if __name__ == "__main__":
    main()
