from parse import source_deps_and_vars 
from textwrap import dedent


class NotebookCellOrganiser:
    def __init__(self, cells):
        self._cells = cells
        self._cell_deps_n_vars = [
            source_deps_and_vars(cell_src) for cell_src in cells]

    def which_cells_need_rerunning(self, cell_id):
        """
        Given an update to a cell, which cells would need re-running.

        """
        updated_vars = set(self._cell_deps_n_vars[cell_id][1])
        updated_cells = []
        cell_id += 1
        for i, (depends, updates) in enumerate(self._cell_deps_n_vars[cell_id:], start=cell_id):
            for dep in depends:
                if dep in updated_vars:
                    updated_cells.append(i)
                    updated_vars.update(updates)
                    break
        return updated_cells


def source_to_cells(source):
    cells = [[]]
    for line in source.split('\n'):
        if len(line) * '-' == line:
            cells.append([])
        else:
            cells[-1].append(line)
    cells = ['\n'.join(cell) for cell in cells]
    return cells


def test_update_variable():
    cells = source_to_cells(dedent(
        """
        a = 1
        print(a)
        ---------------
        a = 3
        print(a)
        ---------------
        b = a + 2
        ---------------
        c = 10
        ---------------
        print(a + c)
        """).strip())
    cs = NotebookCellOrganiser(cells)
    assert cs.which_cells_need_rerunning(0) == [1, 2, 4]
    assert cs.which_cells_need_rerunning(1) == [2, 4]
    assert cs.which_cells_need_rerunning(2) == []
    assert cs.which_cells_need_rerunning(3) == [4]

def test_nested_deps():
    cells = source_to_cells(dedent(
        """
        a = 1
        ---------------
        b = a + 2
        ---------------
        print(b)
        """).strip())
    cs = NotebookCellOrganiser(cells)
    assert cs.which_cells_need_rerunning(0) == [1, 2]
    assert cs.which_cells_need_rerunning(1) == [2]
    assert cs.which_cells_need_rerunning(2) == []


def test_consumer_optimisation():
    cells = source_to_cells(dedent(
        """
        a = 1
        ---------------
        print(a)
        ---------------
        print(a)
        """).strip())
    cs = NotebookCellOrganiser(cells)
    assert cs.which_cells_need_rerunning(0) == [1, 2]
    # Updating the print statement shouldn't require
    # re-running subsequent cells...
    assert cs.which_cells_need_rerunning(1) == []
    assert cs.which_cells_need_rerunning(2) == []
