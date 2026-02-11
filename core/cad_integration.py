"""
AutoCAD 연동 모듈 (AutoCAD Integration)
DWG/DXF 파일에서 객체 정보를 추출하여 산출 시스템과 연동

기능:
- DWG/DXF 파일 열기
- 레이어별 객체 선택 및 필터링
- 객체 정보 추출 (길이, 면적, 개수)
- 산출 항목 자동 생성

참고: egManual.pdf p251-323

의존성:
- ezdxf (pip install ezdxf) - DXF 파일 파싱
- comtypes (Windows) - AutoCAD COM 인터페이스 (선택적)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import math


@dataclass
class CADEntity:
    """CAD 객체 데이터 클래스"""

    entity_type: str  # 객체 유형 (LINE, CIRCLE, POLYLINE, etc.)
    handle: str  # 객체 핸들
    layer: str  # 레이어명
    color: int  # 색상 번호
    line_type: str = ""  # 선스타일

    # 위치 정보
    start_point: tuple = None  # (x, y, z)
    end_point: tuple = None  # (x, y, z)
    center_point: tuple = None  # (x, y, z)

    # 측정 정보
    length: float = 0.0  # 길이 (선 객체)
    area: float = 0.0  # 면적 (면 객체)
    radius: float = 0.0  # 반지름 (원)

    # 사용자 정의 데이터
    attributes: dict = field(default_factory=dict)

    @property
    def bounding_box(self) -> tuple:
        """바운딩 박스 반환"""
        if self.start_point and self.end_point:
            min_x = min(self.start_point[0], self.end_point[0])
            max_x = max(self.start_point[0], self.end_point[0])
            min_y = min(self.start_point[1], self.end_point[1])
            max_y = max(self.start_point[1], self.end_point[1])
            return (min_x, min_y, max_x, max_y)
        return None


@dataclass
class CADLayer:
    """CAD 레이어 데이터 클래스"""

    name: str  # 레이어명
    is_visible: bool = True  # 표시 여부
    color: int = 7  # 레이어 색상
    line_type: str = "Continuous"  # 선스타일
    entity_count: int = 0  # 객체 수
    locked: bool = False  # 잠금 여부


class CADExtractor:
    """
    CAD 파일 추출기
    DXF/DWG 파일에서 객체 및 레이어 정보를 추출
    """

    def __init__(self):
        self.doc = None  # CAD 문서
        self.modelspace = None  # 모델 공간
        self.layers: Dict[str, CADLayer] = {}
        self.entities: List[CADEntity] = []
        self.file_path = None

    def open_file(self, file_path: str) -> bool:
        """
        CAD 파일 열기

        Args:
            file_path: 파일 경로 (.dxf, .dwg)

        Returns:
            성공 여부
        """
        self.file_path = file_path

        try:
            # ezdxf 사용 (DXF 파일용)
            if file_path.lower().endswith(".dxf"):
                import ezdxf

                self.doc = ezdxf.readfile(file_path)
                self.modelspace = self.doc.modelspace()
                self._extract_layers()
                self._extract_entities()
                return True

            # DWG 파일 (comtypes 사용 - Windows 전용)
            elif file_path.lower().endswith(".dwg"):
                # AutoCAD가 설치된 경우 COM으로 접근
                try:
                    return self._open_with_com(file_path)
                except Exception as e:
                    # AutoCAD 미설치 시 메시지
                    print(f"DWG 파일 열기 실패: {e}")
                    return False

            return False

        except Exception as e:
            print(f"파일 열기 오류: {e}")
            return False

    def _open_with_com(self, file_path: str) -> bool:
        """COM 인터페이스로 DWG 파일 열기 (AutoCAD 필요)"""
        try:
            from comtypes.client import GetObject, CreateObject
            import comtypes

            # AutoCAD COM 객체 생성
            acad = CreateObject("AutoCAD.Application")
            acad.Visible = False

            # 문서 열기
            doc = acad.Documents.Open(file_path)
            self.modelspace = doc.ModelSpace

            # 레이어 정보 추출
            for i in range(doc.Layers.Count):
                layer = doc.Layers.Item(i + 1)
                self.layers[layer.Name] = CADLayer(
                    name=layer.Name, is_visible=layer.LayerOn, color=layer.Color
                )

            # 객체 정보 추출
            self._extract_entities_from_com()

            # AutoCAD 종료
            acad.Quit()
            return True

        except Exception as e:
            print(f"COM 연결 실패: {e}")
            return False

    def _extract_layers(self):
        """레이어 정보 추출 (ezdxf)"""
        self.layers = {}

        for layer in self.doc.layers:
            self.layers[layer.dxf.name] = CADLayer(
                name=layer.dxf.name,
                is_visible=layer.dxf.layer_on
                if hasattr(layer.dxf, "layer_on")
                else True,
                color=layer.dxf.color if hasattr(layer.dxf, "color") else 7,
            )

    def _extract_entities(self):
        """객체 정보 추출 (ezdxf)"""
        self.entities = []

        for entity in self.modelspace:
            cad_entity = CADEntity(
                entity_type=entity.dxftype(),
                handle=str(entity.dxf.handle) if hasattr(entity.dxf, "handle") else "",
                layer=entity.dxf.layer if hasattr(entity.dxf, "layer") else "0",
                color=entity.dxf.color if hasattr(entity.dxf, "color") else 7,
            )

            # 객체 유형별 정보 추출
            self._extract_entity_details(entity, cad_entity)

            self.entities.append(cad_entity)
            # 레이어 객체 수 증가
            if cad_entity.layer in self.layers:
                self.layers[cad_entity.layer].entity_count += 1

    def _extract_entities_from_com(self):
        """객체 정보 추출 (COM/AutoCAD)"""
        self.entities = []

        for i in range(self.modelspace.Count):
            entity = self.modelspace.Item(i)
            entity_type = entity.EntityName

            cad_entity = CADEntity(
                entity_type=entity_type,
                handle=str(entity.Handle) if hasattr(entity, "Handle") else "",
                layer=entity.Layer if hasattr(entity, "Layer") else "0",
                color=entity.Color if hasattr(entity, "Color") else 7,
            )

            # 객체 유형별 정보 추출
            self._extract_entity_details_com(entity, cad_entity)

            self.entities.append(cad_entity)
            # 레이어 객체 수 증가
            if cad_entity.layer in self.layers:
                self.layers[cad_entity.layer].entity_count += 1

    def _extract_entity_details(self, entity, cad_entity: CADEntity):
        """ezdxf 객체 상세 정보 추출"""

        if cad_entity.entity_type == "LINE":
            try:
                start = entity.dxf.start
                end = entity.dxf.end
                cad_entity.start_point = (start.x, start.y, start.z)
                cad_entity.end_point = (end.x, end.y, end.z)
                cad_entity.length = start.distance_to(end)
            except:
                pass

        elif cad_entity.entity_type == "CIRCLE":
            try:
                center = entity.dxf.center
                cad_entity.center_point = (center.x, center.y, center.z)
                cad_entity.radius = entity.dxf.radius
                cad_entity.area = math.pi * cad_entity.radius**2
            except:
                pass

        elif cad_entity.entity_type == "LWPOLYLINE":
            try:
                # 다중선 길이 계산
                points = list(entity.get_points())
                if len(points) >= 2:
                    total_length = 0
                    for i in range(len(points) - 1):
                        p1 = points[i]
                        p2 = points[i + 1]
                        total_length += math.sqrt(
                            (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
                        )
                    cad_entity.length = total_length
            except:
                pass

        elif cad_entity.entity_type == "POLYLINE":
            try:
                # 폴리선 길이 계산
                total_length = 0
                for vertex in entity:
                    if hasattr(vertex, "dxf"):
                        prev_vertex = (
                            vertex.virtual_entities()[0]
                            if hasattr(vertex, "virtual_entities")
                            else None
                        )
                        if prev_vertex:
                            total_length += vertex.distance_to(prev_vertex)
                cad_entity.length = total_length
            except:
                pass

        elif cad_entity.entity_type == "ARC":
            try:
                center = entity.dxf.center
                cad_entity.center_point = (center.x, center.y, center.z)
                cad_entity.radius = entity.dxf.radius
                # 호 길이 = 반지름 × 각도(radian)
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                angle_diff = abs(end_angle - start_angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                cad_entity.length = math.radians(angle_diff) * cad_entity.radius
            except:
                pass

    def _extract_entity_details_com(self, entity, cad_entity: CADEntity):
        """COM 객체 상세 정보 추출"""

        entity_type = cad_entity.entity_type

        if "Line" in entity_type:
            try:
                start = entity.StartPoint
                end = entity.EndPoint
                cad_entity.start_point = (start[0], start[1], start[2])
                cad_entity.end_point = (end[0], end[1], end[2])
                cad_entity.length = entity.Length
            except:
                pass

        elif "Circle" in entity_type:
            try:
                center = entity.Center
                cad_entity.center_point = (center[0], center[1], center[2])
                cad_entity.radius = entity.Radius
                cad_entity.area = entity.Area
            except:
                pass

        elif "Polyline" in entity_type:
            try:
                cad_entity.length = entity.Length
            except:
                pass

    def get_entities_by_layer(self, layer_name: str) -> List[CADEntity]:
        """레이어별 객체 조회"""
        return [e for e in self.entities if e.layer == layer_name]

    def get_entities_by_type(self, entity_type: str) -> List[CADEntity]:
        """객체 유형별 조회"""
        return [e for e in self.entities if e.entity_type == entity_type]

    def calculate_layer_total_length(self, layer_name: str) -> float:
        """레이어별 총 길이 계산"""
        entities = self.get_entities_by_layer(layer_name)
        return sum(e.length for e in entities)

    def calculate_layer_total_area(self, layer_name: str) -> float:
        """레이어별 총 면적 계산"""
        entities = self.get_entities_by_layer(layer_name)
        return sum(e.area for e in entities)

    def count_entities(self, layer_name: str = None) -> int:
        """객체 수 계산"""
        if layer_name:
            return len(self.get_entities_by_layer(layer_name))
        return len(self.entities)

    def generate_output_items(self, layer_mapping: Dict[str, Dict]) -> List[Dict]:
        """
        매핑 규칙에 따라 산출 항목 생성

        Args:
            layer_mapping: 레이어별 산출 매핑
            {
                "E-LIGHT": {"name": "전등기", "unit": "개"},
                "E-POWER": {"name": "전원콘센트", "unit": "개"},
                "W-WIRE": {"name": "전선", "unit": "m"}
            }

        Returns:
            산출 항목 목록
        """
        output_items = []

        for layer_name, mapping in layer_mapping.items():
            entities = self.get_entities_by_layer(layer_name)

            if not entities:
                continue

            entity_type = entities[0].entity_type

            # 선 객체: 총 길이
            if entity_type in ["LINE", "LWPOLYLINE", "POLYLINE", "ARC"]:
                total_length = self.calculate_layer_total_length(layer_name)
                output_items.append(
                    {
                        "name": mapping.get("name", layer_name),
                        "spec": mapping.get("spec", ""),
                        "quantity": round(total_length, 2),
                        "unit": mapping.get("unit", "m"),
                        "layer": layer_name,
                        "item_type": "length",
                    }
                )

            # 면 객체: 총 면적
            elif entity_type in ["CIRCLE", "LWPOLYLINE", "HATCH"]:
                total_area = self.calculate_layer_total_area(layer_name)
                output_items.append(
                    {
                        "name": mapping.get("name", layer_name),
                        "spec": mapping.get("spec", ""),
                        "quantity": round(total_area, 2),
                        "unit": mapping.get("unit", "㎡"),
                        "layer": layer_name,
                        "item_type": "area",
                    }
                )

            # 점 객체: 개수
            else:
                count = len(entities)
                output_items.append(
                    {
                        "name": mapping.get("name", layer_name),
                        "spec": mapping.get("spec", ""),
                        "quantity": count,
                        "unit": mapping.get("unit", "개"),
                        "layer": layer_name,
                        "item_type": "count",
                    }
                )

        return output_items

    def get_layer_summary(self) -> List[Dict]:
        """레이어별 요약 정보"""
        summary = []

        for layer_name, layer in self.layers.items():
            entities = self.get_entities_by_layer(layer_name)

            if not entities:
                continue

            total_length = self.calculate_layer_total_length(layer_name)
            total_area = self.calculate_layer_total_area(layer_name)

            summary.append(
                {
                    "layer": layer_name,
                    "entity_count": len(entities),
                    "total_length": round(total_length, 2),
                    "total_area": round(total_area, 2),
                    "visible": layer.is_visible,
                }
            )

        return summary


class AutoCADIntegrationPopup:
    """
    AutoCAD 연동 팝업 (별도 구현 필요)

    이 클래스는 기본 구조를 제공하며,
    실제 팝업 UI는 Qt Designer나 직접 코딩으로 구현
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.extractor = CADExtractor()
        self.layer_mapping = {}

    def load_dwg_file(self, file_path: str) -> bool:
        """DWG/DXF 파일 로드"""
        return self.extractor.open_file(file_path)

    def set_layer_mapping(self, mapping: Dict[str, Dict]):
        """레이어 매핑 설정"""
        self.layer_mapping = mapping

    def get_output_items(self) -> List[Dict]:
        """산출 항목 생성"""
        return self.extractor.generate_output_items(self.layer_mapping)


if __name__ == "__main__":
    # 테스트 코드
    extractor = CADExtractor()

    # DXF 파일 열기 테스트 (실제 파일 경로로 변경)
    # success = extractor.open_file("test.dxf")

    # 레이어 요약 조회
    # summary = extractor.get_layer_summary()

    print("AutoCAD Integration Module")
    print("Install ezdxf: pip install ezdxf")
