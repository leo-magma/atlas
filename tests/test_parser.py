import pytest

from atlas.errors import AtlasSyntaxError
from atlas.parser import parse, tokenize


def test_tokenize_strips_comments():
    assert tokenize("a = b c  # tail") == ["a", "=", "b", "c"]


def test_tokenize_quoted_path():
    assert tokenize('p = load "my file.csv"') == ["p", "=", "load", "my file.csv"]


def test_parse_assignment_and_kwargs():
    cmd = parse(tokenize("rets = returns prices method=log"))
    assert cmd.name == "rets"
    assert cmd.func == "returns"
    assert cmd.arg == "prices"
    assert cmd.args == []
    assert cmd.kwargs == {"method": "log"}


def test_parse_positional_tail():
    cmd = parse(tokenize("v = vol rets 21"))
    assert cmd.arg == "rets"
    assert cmd.args == ["21"]
    assert cmd.kwargs == {}


def test_parse_print():
    cmd = parse(tokenize("print var95"))
    assert cmd.func == "print"
    assert cmd.name is None
    assert cmd.arg == "var95"


def test_parse_errors():
    with pytest.raises(AtlasSyntaxError):
        parse(tokenize("print"))
    with pytest.raises(AtlasSyntaxError):
        parse(tokenize("bad"))
