class Type:
    pass


class IntType(Type):
    def __repr__(self) -> str:
        return "Int"


Int = IntType()  # Singleton


class BoolType(Type):
    def __repr__(self) -> str:
        return "Bool"


Bool = BoolType()


class UnitType(Type):
    def __repr__(self) -> str:
        return "Unit"


Unit = UnitType()


class FunType(Type):
    def __init__(self, params: list[Type], ret: Type):
        self.params = params
        self.ret = ret

    def __repr__(self) -> str:
        params_str = ", ".join(map(str, self.params))
        return f"({params_str}) => {self.ret}"
