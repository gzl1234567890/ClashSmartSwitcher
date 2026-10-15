from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QFocusEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QScrollArea, QVBoxLayout, QWidget
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
    layout.addStretch()
    host.resize(520, 200)
    qtbot.addWidget(host)
    host.show()
    host.activateWindow()
    qtbot.waitUntil(host.isVisible)
    qtbot.wait(20)
    field._test_host = host
    field._test_outside = outside
    return field


def click_option(qtbot, field, region):
    item = next(field.options.item(i) for i in range(field.options.count())
                if field.options.item(i).data(Qt.UserRole) == region)
    field.options.scrollToItem(item)
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


def send_wheel(window, target, delta, native=True):
    point = target.mapToGlobal(target.rect().center())
    # QTest.wheelEvent mis-scales global coordinates on Windows at 150% DPI.
    receiver = window.windowHandle() if native else target
    event = QWheelEvent(QPointF((window if native else target).mapFromGlobal(point)), QPointF(point), QPoint(),
                        QPoint(0, delta), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    QApplication.sendEvent(receiver, event)


@pytest.mark.parametrize("delivery", ["window", "viewport"])
def test_wheel_scroll_preserves_popup_search_and_selection(qtbot, field, delivery):
    field._test_host.resize(600, 600)
    field.set_available_regions([f"地区{i:02}" for i in range(40)])
    field.set_selected_regions(["香港", "地区00"])
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    field.editor.setText("地区")
    qtbot.wait(20)
    assert field.popup.isVisible()
    geometry = field.popup.geometry()
    changes = []
    field.selection_changed.connect(changes.append)
    scroll = field.options.verticalScrollBar()
    assert scroll.maximum() > 0

    def wheel(delta):
        send_wheel(field.popup, field.options.viewport(), delta, native=delivery == "window")
        assert field.popup.isVisible()
        assert field.popup.geometry() == geometry
        assert field.editor.text() == "地区"
        assert field.selected_regions() == ["香港", "地区00"]
        assert not changes

    # Scroll upward at the top, through the middle, beyond the bottom, and back.
    wheel(120)
    assert scroll.value() == scroll.minimum()
    wheel(-120)
    assert scroll.value() > scroll.minimum()
    for _ in range(field.options.count() + 5):
        wheel(-120)
    assert scroll.value() == scroll.maximum()
    for _ in range(field.options.count() + 5):
        wheel(120)
    assert scroll.value() == scroll.minimum()
    assert field.options.item(0).checkState() == Qt.Checked
    click_option(qtbot, field, "地区01")
    assert field.selected_regions() == ["香港", "地区00", "地区01"]
    click_option(qtbot, field, "地区01")
    assert field.selected_regions() == ["香港", "地区00"]
    qtbot.mouseClick(chips(field)[0].remove_button, Qt.LeftButton)
    assert field.selected_regions() == ["地区00"]
    qtbot.mouseClick(field.clear_button, Qt.LeftButton)
    assert field.selected_regions() == []
    assert field.editor.text() == ""
    assert field.popup.isVisible()
    qtbot.keyClick(field.editor, Qt.Key_Escape)
    assert not field.popup.isVisible()
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    outside = field._test_host.rect().bottomRight() - QPoint(10, 10)
    assert not field.popup.rect().contains(field.popup.mapFromGlobal(field._test_host.mapToGlobal(outside)))
    qtbot.mouseClick(field._test_host, Qt.LeftButton, pos=outside)
    assert not field.popup.isVisible()


@pytest.mark.parametrize("surface", ["viewport", "scrollbar", "frame", "popup"])
def test_wheel_at_popup_boundaries_does_not_close(qtbot, field, surface):
    field.set_available_regions([f"地区{i:02}" for i in range(40)])
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    target = {"viewport": field.options.viewport(), "scrollbar": field.options.verticalScrollBar(),
              "frame": field.popup.findChild(QWidget, "regionMenu"), "popup": field.popup}[surface]
    for delta in (120, -120, 120):
        position = QPointF(target.rect().center())
        event = QWheelEvent(position, QPointF(target.mapToGlobal(position.toPoint())),
                            QPoint(), QPoint(0, delta), Qt.NoButton, Qt.NoModifier,
                            Qt.ScrollUpdate, False)
        QApplication.sendEvent(target, event)
        assert field.popup.isVisible()


def test_native_mouse_clicks_inside_popup_and_input_toggle(qtbot, field):
    point = field.editor.mapToGlobal(field.editor.rect().center())
    window = field._test_host
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, Qt.NoModifier, window.mapFromGlobal(point))
    assert field.popup.isVisible()
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, Qt.NoModifier, window.mapFromGlobal(point))
    assert not field.popup.isVisible()
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, Qt.NoModifier, window.mapFromGlobal(point))
    item = field.options.item(1)
    point = field.options.viewport().mapToGlobal(field.options.visualItemRect(item).center())
    QTest.mouseClick(field.popup.windowHandle(), Qt.LeftButton, Qt.NoModifier, field.popup.mapFromGlobal(point))
    assert field.selected_regions() == ["新加坡"]
    assert field.popup.isVisible()


def test_outside_wheel_keeps_page_scroll_and_listener_cleanup(qtbot, field):
    page = QScrollArea()
    content = QWidget()
    content.setMinimumHeight(2500)
    page.setWidget(content)
    field._test_host.layout().addWidget(page)
    field._test_host.resize(600, 700)
    qtbot.wait(20)
    for _ in range(3):
        field.show_popup()
        field.hide_popup()
    field.show_popup()
    send_wheel(field._test_host, page.viewport(), -120)
    assert not field.popup.isVisible()
    assert page.verticalScrollBar().value() > 0
    field.show_popup()
    field.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    previous = page.verticalScrollBar().value()
    send_wheel(field._test_host, page.viewport(), -120)
    assert page.verticalScrollBar().value() > previous


def test_internal_style_focus_event_is_not_external_user_focus(qtbot, field):
    field.set_selected_regions(["香港"])
    qtbot.mouseClick(field.editor, Qt.LeftButton)
    QApplication.sendEvent(field.style(), QFocusEvent(QEvent.FocusIn))
    assert field.popup.isVisible()
    assert field.selected_regions() == ["香港"]
    field._test_outside.setFocus()
    qtbot.wait(20)
    assert not field.popup.isVisible()
