from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
import pytest

from smart_switcher.region_select import RegionChip, RegionMultiSelect
from smart_switcher.regions import available_regions, excluded_region


@pytest.fixture
def field(qtbot):
    host = QWidget()
    layout = QVBoxLayout(host)
    field = RegionMultiSelect()
    field.set_available_regions(["香港", "新加坡", "台湾", "日本"])
    outside = QLineEdit()
    layout.addWidget(field)
    layout.addWidget(outside)
    host.resize(520, 200)
    qtbot.addWidget(host)
    host.show()
    host.activateWindow()
    qtbot.waitUntil(host.isVisible)
    field._test_host = host
    field._test_outside = outside
    return field


def click_option(qtbot, field, region):
    item = next(field.options.item(i) for i in range(field.options.count())
                if field.options.item(i).data(Qt.UserRole) == region)
    qtbot.mouseClick(field.options.viewport(), Qt.LeftButton,
                     pos=field.options.visualItemRect(item).center())


def chips(field):
    return [field.flow.itemAt(i).widget() for i in range(field.flow.count())
            if isinstance(field.flow.itemAt(i).widget(), RegionChip)]


def test_click_multiselect_toggle_and_search(qtbot, field):
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    assert field.popup.isVisible()
    for region in ("香港", "新加坡", "台湾"):
        click_option(qtbot, field, region)
        assert field.popup.isVisible()
    assert field.selected_regions() == ["香港", "新加坡", "台湾"]
    assert [chip.region for chip in chips(field)] == field.selected_regions()
    field.editor.setText("台")
    assert field.options.count() == 1
    assert field.options.item(0).checkState() == Qt.Checked
    click_option(qtbot, field, "台湾")
    assert field.selected_regions() == ["香港", "新加坡"]
    field.editor.setText("SG")
    assert field.options.count() == 1
    assert field.options.item(0).data(Qt.UserRole) == "新加坡"
    assert field.options.item(0).checkState() == Qt.Checked
    assert field.selected_regions() == ["香港", "新加坡"]


@pytest.mark.parametrize("opened", [False, True])
def test_remove_and_clear_preserve_popup_state(qtbot, field, opened):
    field.set_selected_regions(["香港", "新加坡", "台湾"])
    if opened:
        qtbot.mouseClick(field.editor, Qt.LeftButton)
    qtbot.mouseClick(chips(field)[1].remove_button, Qt.LeftButton)
    assert field.selected_regions() == ["香港", "台湾"]
    assert field.popup.isVisible() == opened
    qtbot.mouseClick(field.clear_button, Qt.LeftButton)
    assert not field.selected_regions()
    assert not chips(field)
    assert field.popup.isVisible() == opened
    assert field.editor.placeholderText() == "请选择或搜索地区"
    assert not field.clear_button.isVisible()


def test_outside_escape_and_keyboard_navigation(qtbot, field):
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    qtbot.keyClick(field.editor, Qt.Key_Down)
    qtbot.keyClick(field.editor, Qt.Key_Return)
    assert field.selected_regions() == ["新加坡"]
    assert field.popup.isVisible()
    qtbot.keyClick(field.editor, Qt.Key_Escape)
    assert not field.popup.isVisible()
    qtbot.keyClick(field.editor, Qt.Key_Up)
    assert field.popup.isVisible()
    assert field.options.currentRow() == 3
    qtbot.keyClick(field.editor, Qt.Key_Return)
    assert field.selected_regions() == ["新加坡", "日本"]
    qtbot.mouseClick(field._test_outside, Qt.LeftButton)
    assert not field.popup.isVisible()
    assert field.selected_regions() == ["新加坡", "日本"]


def test_empty_search_and_custom_region(qtbot, field):
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    field.set_selected_regions(["香港"])
    field.editor.setText("自定义节点区")
    assert field.empty_label.isVisible()
    assert field.empty_label.text() == "未找到匹配地区"
    qtbot.keyClick(field.editor, Qt.Key_Return)
    assert field.selected_regions() == ["香港", "自定义节点区"]
    assert field.options.item(0).checkState() == Qt.Checked
    assert excluded_region("自定义节点区 01", field.selected_regions()) == "自定义节点区"
    field.editor.setText("")
    field.set_available_regions(["德国"])
    assert [field.options.item(i).text() for i in range(field.options.count())] == [
        "德国", "香港", "自定义节点区"]
    field.setEnabled(False)
    assert not field.popup.isVisible()
    field.show_popup()
    assert not field.popup.isVisible()


def test_clear_query_does_not_reopen_closed_menu(qtbot, field):
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    field.set_selected_regions(["香港"])
    field.editor.setText("台")
    qtbot.keyClick(field.editor, Qt.Key_Escape)
    field.clear()
    assert not field.popup.isVisible()
    assert field.editor.text() == ""
    assert field.selected_regions() == []


def test_wrapping_and_popup_screen_bounds(qtbot, field):
    field._test_host.resize(340, 450)
    field.set_selected_regions(["香港", "新加坡", "台湾", "日本", "很长的自定义地区名称" * 8])
    qtbot.wait(50)
    visible_chips = chips(field)
    assert len({chip.y() for chip in visible_chips}) > 1
    for chip in visible_chips:
        assert field.content.rect().contains(chip.geometry())
    assert field.content.rect().contains(field.editor.geometry())
    for index, first in enumerate(visible_chips):
        for second in visible_chips[index + 1:]:
            assert not first.geometry().intersects(second.geometry())
    field._test_host.move(30, field.screen().availableGeometry().bottom() - 150)
    field.show_popup()
    assert field.popup.isWindow()
    assert field.screen().availableGeometry().contains(field.popup.geometry())


def test_discovery_uses_real_names_and_shared_exclusion_rules():
    names = ["HK01", "Singapore SG", "🇹🇼 01", "Japan 02", "JP03", "DE-01", "未识别节点"]
    assert available_regions(names) == ["香港", "新加坡", "台湾", "日本", "德国"]
    for name in names[:-1]:
        regions = available_regions([name])
        assert regions
        assert excluded_region(name, regions) in regions
    assert available_regions(["ASGARD", "SINGER", "HKEY", "SGermany", "JProxy"]) == []
    assert available_regions([]) == []
    assert available_regions(["印度尼西亚 01"]) == ["印度尼西亚"]
    assert excluded_region("印度尼西亚 01", ["印度"]) is None
