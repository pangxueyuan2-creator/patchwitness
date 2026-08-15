from patchwitness.git import _parse_name_status_z, _parse_numstat_z


def test_parse_name_status_z_unicode_rename() -> None:
    payload = "R100\0计算.py\0calc_cn.py\0M\0readme.md\0"
    assert _parse_name_status_z(payload) == [
        ("calc_cn.py", "R100", "计算.py"),
        ("readme.md", "M", None),
    ]


def test_cquoted_tab_parser_mangles_unicode_previous_path() -> None:
    """Document why collect_changes must use -z, not tab-split + replace('\\','/')."""

    line = 'R100\t"\\350\\256\\241\\347\\256\\227.py"\tcalc_cn.py'
    parts = line.split("\t")
    previous = parts[-2].replace("\\", "/")
    assert previous != "计算.py"
    assert "计算.py" not in previous


def test_parse_numstat_z_regular_and_rename() -> None:
    # Keep NULs explicit: "\03" is octal ESC, not NUL + "3".
    payload = "4\t1\tsrc/app.py\0-\t-\tphoto.bin\0" + "3\t1\t\0计算.py\0calc_cn.py\0"
    stats = _parse_numstat_z(payload)
    assert stats["src/app.py"] == (4, 1, False)
    assert stats["photo.bin"] == (0, 0, True)
    assert stats["calc_cn.py"] == (3, 1, False)
    assert "" not in stats
