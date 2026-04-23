from lang_loop.loop_ast import *
from common.wasm import *
from common.compilerSupport import *
import lang_loop.loop_tychecker as loop_tychecker


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """

    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(identifier.name), typeToWasmType(vartype.ty)) for identifier, vartype in vars.items()]

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
            
            case IfStmt(cond, thenBody, elseBody):
                if_instrs = compileExpr(cond)
                then_instrs = compileStmts(thenBody)
                else_instrs = compileStmts(elseBody)

                if_instrs.append(WasmInstrIf(None, then_instrs, else_instrs))
                instrs.extend(if_instrs)

            case WhileStmt(cond, body):
                loop_label = WasmId('$loop_start') 
                exit_label = WasmId('$loop_exit')
                
                # Code für die Bedingung
                cond_instrs = compileExpr(cond)
                # Body der Schleife + Rücksprung
                body_instrs = compileStmts(body) + [WasmInstrBranch(loop_label, conditional=False)]
                
                # Die Struktur von Folie 26:
                # Wenn Bedingung falsch (0), springe zum exit_label
                inner_instrs = cond_instrs + [
                    WasmInstrIf(None, [], [WasmInstrBranch(exit_label, conditional=False)]),
                    *body_instrs
                ]
                
                instrs.append(
                    WasmInstrBlock(exit_label, None, [
                        WasmInstrLoop(loop_label, inner_instrs)
                    ])
                )
                
    return instrs


def compileExpr(e: exp) -> list[WasmInstr]:
    """
    Compiles the given expression.
    """
    match e:
        case IntConst(value):
            return [WasmInstrConst('i64', value)]
        
        case BoolConst(value):
            return [WasmInstrConst('i32', 1 if value else 0)]
        
        case Name(ident):
            return [WasmInstrVarLocal('get',identToWasmId(ident.name))]
        
        case BinOp(left, op, right):
            if not isinstance(op, (And, Or)):
                instrs = compileExpr(left)
                instrs.extend(compileExpr(right))
                
                # Bestimme den Wasm-Typ basierend auf dem Typ der Operanden
                left_ty = tyOfExp(left)
                wasm_op_ty = 'i32' if isinstance(left_ty, Bool) else 'i64'
                
                match op:
                    case Add(): instrs.append(WasmInstrNumBinOp('i64', 'add'))
                    case Sub(): instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                    case Mul(): instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                    # Hier nutzt du jetzt wasm_op_ty statt fest i64!
                    case Less(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'lt_s'))
                    case LessEq(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'le_s'))
                    case Greater(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'gt_s'))
                    case GreaterEq(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'ge_s'))
                    case Eq(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'eq'))
                    case NotEq(): instrs.append(WasmInstrIntRelOp(wasm_op_ty, 'ne'))
                return instrs
            else:
                # --- Teil 2: Logik mit Short-Circuiting ---
                l_code = compileExpr(left)
                r_code = compileExpr(right)
                
                match op:
                    case And():
                        # if A then B else False
                        return l_code + [WasmInstrIf('i32', r_code, [WasmInstrConst('i32', 0)])]
                    case Or():
                        # if A then True else B
                        return l_code + [WasmInstrIf('i32', [WasmInstrConst('i32', 1)], r_code)]
                
        
        case UnOp(op, arg):
            match op:
                case USub():
                    return [WasmInstrConst('i64', 0)] + compileExpr(arg) + [WasmInstrNumBinOp('i64', 'sub')]
                case Not():
                    return compileExpr(arg) + [WasmInstrConst('i32', 0)] + [WasmInstrIntRelOp('i32', 'eq')]
        
        case Call(ident, args):
            instrs: list[WasmInstr] = []
            for arg in args:
                instrs.extend(compileExpr(arg))
            
            if ident.name == 'print':
                # Wir schauen uns den Typ des ersten Arguments an
                arg_type = tyOfExp(args[0])
                
                # Wenn es ein Bool ist, rufen wir print_bool (i32) auf
                if isinstance(arg_type, Bool):
                    instrs.append(WasmInstrCall(WasmId('$print_bool')))
                else:
                    # Ansonsten print_i64
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

def typeToWasmType(ty: ty) -> WasmValtype:
    """
    Konvertiert einen Loop-Typ in einen Wasm-Typ.
    """
    
    match ty:
        case Int(): return 'i64'
        case Bool(): return 'i32'

def tyOfExp(e: exp) -> ty:
    match e:
        case IntConst(_): return Int()
        case BoolConst(_): return Bool()
        case Name(ident_obj, ty_attr):
            if isinstance(ty_attr, NotVoid): return ty_attr.ty
            raise Exception(f"Variable {ident_obj.name} has no type info")
        case BinOp(_, op, _):
            if isinstance(op, (Add, Sub, Mul)): return Int()
            return Bool()
        case UnOp(op, _):
            return Int() if isinstance(op, USub) else Bool()
        case Call(ident, _, ty_attr):
            if ident.name == 'input_int': return Int()
            if isinstance(ty_attr, NotVoid): return ty_attr.ty
            raise Exception(f"Call to {ident.name} has no type info")
    raise Exception(f"Unknown expression type: {type(e)}")