from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
#import common.utils as utils


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """

    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x.name), 'i64') for x in vars]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    """
    Compiles the given statements.
    """
    instrs: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case StmtExp(expr):
                instrs.extend(compileExpr(expr))

                is_print = isinstance(expr, Call) and expr.name.name == 'print'
                if not is_print:
                    instrs.append(WasmInstrDrop())

            case Assign(ident, expr):
                instrs.extend(compileExpr(expr))
                instrs.append(WasmInstrVarLocal('set',identToWasmId(ident.name)))
                pass
    return instrs


def compileExpr(e: exp) -> list[WasmInstr]:
    """
    Compiles the given expression.
    """
    match e:
        case IntConst(value):
            return [WasmInstrConst('i64', value)]
        
        case Name(ident):
            return [WasmInstrVarLocal('get',identToWasmId(ident.name))]
        
        case BinOp(left, op, right):
            instrs = compileExpr(left)
            instrs.extend(compileExpr(right))
            match op:
                case Add(): instrs.append(WasmInstrNumBinOp('i64', 'add'))
                case Sub(): instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                case Mul(): instrs.append(WasmInstrNumBinOp('i64', 'mul'))
            return instrs
        
        case UnOp(USub(), arg):
            return [WasmInstrConst('i64', 0)] + compileExpr(arg) + [WasmInstrNumBinOp('i64', 'sub')]
        
        case Call(ident, args):
            instrs: list[WasmInstr] = []
            for arg in args:
                instrs.extend(compileExpr(arg))
            
            if ident.name == 'print':
                instrs.append(WasmInstrCall(WasmId('$print_i64')))
            
            elif  ident.name == 'input_int':
                instrs.append(WasmInstrCall(WasmId('$input_i64')))
            
            else:
                raise Exception(f"Unknown function: {ident.name}")
            return instrs

def identToWasmId(name: str) -> WasmId:
    """
    Konvertiert einen Identifier-String in eine Wasm-ID (z.B. x -> $x).
    """
    return WasmId(f"${name}")