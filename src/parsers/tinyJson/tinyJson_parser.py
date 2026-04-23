from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    toks.ensureNext("LBRACE")
    entryList = ruleEntryList(toks)
    toks.ensureNext("RBRACE")
    return entryList

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    if toks.lookahead().type == 'STRING':
        return ruleEntryListNotEmpty(toks)
    else:
        return {}

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    entry = ruleEntry(toks)

    if toks.lookahead().type == 'COMMA':
        toks.next()
        entryListNotEmpty = ruleEntryListNotEmpty(toks)
        entryListNotEmpty[entry[0]] = entry[1]
        return entryListNotEmpty
    else:
        return {entry[0]: entry[1]} 

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    key = ruleString(toks)
    toks.ensureNext("COLON")
    json = ruleJson(toks)

    return (key, json) 

def ruleString(toks: TokenStream) -> str:
    string = toks.ensureNext("STRING").value
    return string[1:-1] 

def ruleInt(toks: TokenStream) -> int:
    value = toks.ensureNext("INT").value
    return int(value) 

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
