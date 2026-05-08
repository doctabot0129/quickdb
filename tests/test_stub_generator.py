from quickdb.scripts.stub_generator import _to_pascal_case, _class_to_filename


def test_to_pascal_case_single_word():
    assert _to_pascal_case('cases') == 'Cases'


def test_to_pascal_case_snake_case():
    assert _to_pascal_case('case_updates') == 'CaseUpdates'


def test_to_pascal_case_single_segment():
    assert _to_pascal_case('suitecrm') == 'Suitecrm'


def test_to_pascal_case_multi_segment():
    assert _to_pascal_case('my_warehouse') == 'MyWarehouse'


def test_class_to_filename_sqlserver():
    assert _class_to_filename('SQLServer') == 'sql_server.pyi'


def test_class_to_filename_suitecrm():
    assert _class_to_filename('SuiteCRMServer') == 'suite_crm_server.pyi'


def test_class_to_filename_mariadb():
    assert _class_to_filename('MariaDBServer') == 'maria_db_server.pyi'


def test_class_to_filename_simple():
    assert _class_to_filename('MyServer') == 'my_server.pyi'


from quickdb.scripts.stub_generator import _generate_table_stub


def test_table_stub_class_name():
    result = _generate_table_stub('cases', ['id', 'name'])
    assert 'class _CasesTable(SQLTable):' in result


def test_table_stub_snake_case_name():
    result = _generate_table_stub('case_updates', ['id'])
    assert 'class _CaseUpdatesTable(SQLTable):' in result


def test_table_stub_column_attrs():
    result = _generate_table_stub('cases', ['id', 'name', 'entered_date'])
    assert '    id: str' in result
    assert '    name: str' in result
    assert '    entered_date: str' in result


def test_table_stub_literal_fields_in_limited_query():
    result = _generate_table_stub('cases', ['id', 'name'])
    assert "Literal['id', 'name']" in result
    assert '-> pd.DataFrame: ...' in result


def test_table_stub_skips_python_keywords():
    result = _generate_table_stub('orders', ['id', 'from', 'return'])
    assert '    id: str' in result
    assert '    from: str' not in result
    assert '    return: str' not in result


def test_table_stub_skips_non_identifiers():
    result = _generate_table_stub('orders', ['id', '1bad', 'has space'])
    assert '    id: str' in result
    assert '    1bad: str' not in result
    assert '    has space: str' not in result


def test_table_stub_no_valid_columns_uses_generic_fields_type():
    result = _generate_table_stub('orders', ['from', 'return'])
    assert 'list[str] | None' in result
    assert 'Literal' not in result


from quickdb.scripts.stub_generator import _generate_database_stub


def test_database_stub_class_name():
    result = _generate_database_stub('suitecrm', ['cases', 'accounts'])
    assert 'class _SuitecrmDb(SQLDatabase):' in result


def test_database_stub_snake_case_name():
    result = _generate_database_stub('my_warehouse', ['orders'])
    assert 'class _MyWarehouseDb(SQLDatabase):' in result


def test_database_stub_table_attrs():
    result = _generate_database_stub('suitecrm', ['cases', 'accounts'])
    assert '    cases: _CasesTable' in result
    assert '    accounts: _AccountsTable' in result


def test_database_stub_no_tables_emits_pass():
    result = _generate_database_stub('empty_db', [])
    assert 'class _EmptyDbDb(SQLDatabase):' in result
    assert '    pass' in result
