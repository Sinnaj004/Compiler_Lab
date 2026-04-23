from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    toks.ensureNext("LBRACE")
    entryList = ruleEntryList(toks)
    toks.ensureNext("RBRACE")
    return entryList # TODO

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    if toks.lookahead().type == 'STRING':
        return ruleEntryListNotEmpty(toks)
    else:
        return {}
    # TODO

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    entry = ruleEntry(toks)

    if toks.lookahead().type == 'COMMA':
        toks.next()
        entryListNotEmpty = ruleEntryListNotEmpty(toks)
        entryListNotEmpty[entry[0]] = entry[1]
        return entryListNotEmpty
    else:
        return {entry[0]: entry[1]} # TODO

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    string:str = toks.ensureNext("STRING").value
    toks.ensureNext("COLON")
    json = ruleJson(toks)

    return (string, json) # TODO

def ruleString(toks: TokenStream) -> str:
    return  toks.ensureNext("STRING").value # TODO

def ruleInt(toks: TokenStream) -> int:
    value = toks.ensureNext("INT").value
    return value # TODO

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
