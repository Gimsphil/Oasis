# -*- coding: utf-8 -*-
"""
PDF 산출 데이터 모델
DrawingElement: 도면 위 그리기 요소 (선, 사각형 등)
OutputItem: 산출 항목 (터파기, 배관, TRAY 등)
"""
from dataclasses import dataclass, field
from typing import Optional, List
from PyQt6.QtCore import QPointF


@dataclass
class DrawingElement:
    """도면 위 그리기 요소"""
    element_type: str  # "line" | "rect"
    points: List[QPointF] = field(default_factory=list)
    start_point: Optional[QPointF] = None
    end_point: Optional[QPointF] = None
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0
    length: float = 0.0
    color: str = "#000000"
    line_width: float = 2.0
    label: str = ""
    notes: str = ""
    quantity: float = 0.0
    unit: str = "m"


@dataclass
class OutputItem:
    """산출 항목"""
    id: int
    output_type: str
    location: str
    specification: str
    length: float
    width: float = 0.0
    depth: float = 0.0
    area: float = 0.0
    quantity: float = 0.0
    unit: str = "m³"
    notes: str = ""
