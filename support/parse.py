from textwrap import dedent
import ast
import collections


class Inspector(ast.NodeVisitor):
    def visit(self, node):
        print('FOO: ', type(node).__name__)
        super().visit(node)

    def visit_Module(self, node):
        self.context_depth = 0
        self.consumes = []
        # Variables that we know are not updates, but entirely
        # independently defined by this module. All vars in this
        # list are guaranteed independent, however some vars in consumes
        # may also be independent.
        self.exclusive_vars = []
        self.updates = []
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Note: we don't even try to recurse back to figure out whether the
        # assignment makes use of consumes. i.e. "a = a + 10" vs "a = 10".
        # The problem is really hard, as it could be obfuscated, e.g.
        # "b = a; a = b + 10"

        if self.context_depth == 0:
            self.updates.extend([target.id for target in node.targets])
        self.visit(node.value)

    def visit_Global(self, node):
        self.updates.extend(node.names)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.context_depth += 1
        # If we are defining a function, we can't be re-using the existing
        # one (capturing an existing one as another variable will have been
        # caught separately).
        if self.context_depth <= 1:
            print('Add independent var:', node.name)
            self.exclusive_vars.append(node.name)
            self.updates.append(node.name)
        self.generic_visit(node)
#        self.exclusive_vars = []
        self.context_depth -= 1

    def visit_Name(self, node):
        # Only non-assigned variable names make it through
        # to here (see visit_Assign).
        if node.id not in self.exclusive_vars:
            print('Add dependency:', node.id)
            self.consumes.append(node.id)
        self.generic_visit(node)

    def visit_arguments(self, node):
        for arg in node.args:
            self.exclusive_vars.append(arg.arg)
        self.generic_visit(node)

def drop_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def source_deps_and_vars(code):
    i = Inspector()
    i.visit(ast.parse(code))
    return drop_duplicates(i.consumes), drop_duplicates(i.updates)


def test_simple_assign():
    code = "a=1"
    depends, creates = source_deps_and_vars(code)
    assert depends == []
    assert creates == ['a']


def test_simple_assign_w_print():
    code = "a=1; print(a)"
    depends, creates = source_deps_and_vars(code)
    # NOTE: In theory, we could avoid the dependency on "a" as
    # we have an independent assignment here. However, this is a bit
    # trickier to implement...
    assert depends == ['print', 'a']
    assert creates == ['a']


def test_simple_depend_w_print():
    code = "print(b)"
    depends, creates = source_deps_and_vars(code)
    assert depends == ['print', 'b']
    assert creates == []


def test_global():
    code = dedent("""
    def update_a(value):
        global a
        a = value
    update_a(20)
    """)
    depends, creates = source_deps_and_vars(code)
    assert depends == []
    assert creates == ['update_a', 'a']


def test_non_global():
    code = dedent("""
    def update_a(value):
        a = value
    update_a(20)
    """)
    depends, creates = source_deps_and_vars(code)
    assert depends == []
    assert creates == ['update_a']


def test_global_update():
    code = dedent("""
    def update_a(value):
        global a
        a = b + value
    update_a(20)
    """)
    depends, creates = source_deps_and_vars(code)
    assert depends == ['b']
    assert creates == ['update_a', 'a']


def test_func_exclusive():
    code = dedent("""
    def a():
        def b():
            pass
    a = b
    """)
    depends, creates = source_deps_and_vars(code)
    assert depends == ['b']
    assert creates == ['a']


if __name__ == '__main__':
    i = Inspector()
    i.visit(root)
    print('Mod deps:', i.updates)
    print('Mod creates:', i.consumes)

