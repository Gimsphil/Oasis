# -*- coding: utf-8 -*-
"""
견적 변환 옵션 팝업 (Estimate Options Popup)
======================================
산출 → 견적 변환 옵션 설정
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QLabel,
    QMessageBox,
)


class EstimateOptionsPopup(QDialog):
    """견적 변환 옵션 팝업"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("내역작성 옵션")
        self.resize(400, 300)

        self.options = self._get_default_options()
        self._setup_ui()

    def _get_default_options(self):
        """기본 옵션 반환"""
        return {
            "material_surcharge": False,  # 재료할증
            "surcharge_rate": 10.0,  # 할증율 (%)
            "qty_decimal": "정수",  # 정수/1자리/2자리
            "include_under_1": True,  # 1이하 포함
            "floor_by_floor": False,  # 1:1 층별
            "reuse_unit_price": False,  # 기존 단가 재사용
        }

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 그룹 1: 재료할증
        group1 = QGroupBox("재료할증")
        group1_layout = QVBoxLayout()

        self.chk_surcharge = QCheckBox("재료할증 적용 (%):")
        self.chk_surcharge.stateChanged.connect(self._toggle_surcharge)
        group1_layout.addWidget(self.chk_surcharge)

        self.surcharge_layout = QHBoxLayout()
        self.surcharge_layout.addWidget(QLabel("할증율:"))
        self.cmb_surcharge = QComboBox()
        self.cmb_surcharge.addItems(["5%", "10%", "15%", "20%", "30%"])
        self.cmb_surcharge.setCurrentText("10%")
        self.surcharge_layout.addWidget(self.cmb_surcharge)
        self.surcharge_layout.addStretch()
        group1_layout.addLayout(self.surcharge_layout)
        group1.setLayout(group1_layout)
        layout.addWidget(group1)

        # 그룹 2: 수량 소수점
        group2 = QGroupBox("수량 소수점")
        group2_layout = QVBoxLayout()

        self.qty_group = QButtonGroup()
        self.rb_qty_int = QRadioButton("정수 (반올림)")
        self.rb_qty_1 = QRadioButton("소수 1자리")
        self.rb_qty_2 = QRadioButton("소수 2자리")
        self.rb_qty_int.setChecked(True)

        self.qty_group.addButton(self.rb_qty_int)
        self.qty_group.addButton(self.rb_qty_1)
        self.qty_group.addButton(self.rb_qty_2)

        group2_layout.addWidget(self.rb_qty_int)
        group2_layout.addWidget(self.rb_qty_1)
        group2_layout.addWidget(self.rb_qty_2)
        group2.setLayout(group2_layout)
        layout.addWidget(group2)

        # 그룹 3: 기타 옵션
        group3 = QGroupBox("기타 옵션")
        group3_layout = QVBoxLayout()

        self.chk_include_under_1 = QCheckBox("수량 1이하 포함")
        self.chk_include_under_1.setChecked(True)
        group3_layout.addWidget(self.chk_include_under_1)

        self.chk_floor_by_floor = QCheckBox("1:1 층별 작성 (계층 무시)")
        group3_layout.addWidget(self.chk_floor_by_floor)

        self.chk_reuse_unit_price = QCheckBox("이전 단가 재사용")
        group3_layout.addWidget(self.chk_reuse_unit_price)

        group3.setLayout(group3_layout)
        layout.addWidget(group3)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("확인")
        btn_ok.clicked.connect(self._accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        # 초기 상태
        self._toggle_surcharge(0)

    def _toggle_surcharge(self, state):
        """재료할증 체크 상태 변경"""
        enabled = state == 2  # Checked
        for widget in [self.cmb_surcharge]:
            widget.setEnabled(enabled)

    def _accept(self):
        """확인 버튼"""
        # 옵션 수집
        self.options = {
            "material_surcharge": self.chk_surcharge.isChecked(),
            "surcharge_rate": float(self.cmb_surcharge.currentText().replace("%", "")),
            "qty_decimal": "정수"
            if self.rb_qty_int.isChecked()
            else ("1자리" if self.rb_qty_1.isChecked() else "2자리"),
            "include_under_1": self.chk_include_under_1.isChecked(),
            "floor_by_floor": self.chk_floor_by_floor.isChecked(),
            "reuse_unit_price": self.chk_reuse_unit_price.isChecked(),
        }
        self.accept()

    def get_options(self):
        """옵션 반환"""
        return self.options


# ============== 테스트 ==============
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    popup = EstimateOptionsPopup()
    if popup.exec() == QDialog.DialogCode.Accepted:
        print("옵션:", popup.get_options())

    sys.exit()
