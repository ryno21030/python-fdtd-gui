# FDTD 시뮬레이터 GUI

FDTD (Finite-Difference Time-Domain) 전자파 시뮬레이터의 PyQt6 기반 GUI 버전

## 설치

### 요구사항
- Python 3.8 이상
- PyQt6, pyqtgraph, numpy

### 설치 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 애플리케이션 실행
python main.py
```

## 디렉토리 구조

```
fdtd_gui/
├── main.py              # 메인 진입점
├── mainwindow.py        # GUI 메인 윈도우
├── config.py            # 설정 데이터 클래스
├── runner.py            # 시뮬레이션 엔진
├── theme.py             # UI 테마
├── panels/              # GUI 패널들
│   ├── __init__.py
│   ├── _base.py         # 공통 위젯
│   ├── grid.py          # 격자 설정
│   ├── source.py        # 광원 설정
│   ├── material.py      # 재질 설정
│   ├── detector.py      # 검광기 설정
│   ├── pml.py           # PML 경계 설정
│   └── visualize.py     # 결과 시각화
├── saves/               # 시뮬레이션 결과 저장 폴더 (자동 생성)
├── requirements.txt     # 파이썬 의존성
└── README.md            # 이 파일
```

## 사용 방법

1. **설정**: 각 탭에서 시뮬레이션 파라미터 입력
   - 격자 / 시간: 계산 영역 크기 및 시간 설정
   - 광원: 전자파 소스 위치 및 특성
   - 재질 / 구조: 매질의 유전율, 투자율, 전도율
   - 검광기: 결과 저장 위치
   - PML: 경계 흡수 조건

2. **실행**: "▶ 시뮬레이션 실행" 버튼
   - 진행률 표시
   - 완료 후 자동 저장 (saves/frames_TIMESTAMP/)

3. **시각화**: 시각화 탭에서
   - 파일 선택: 저장된 frames.npz 선택
   - 필드 선택: Ez, Ex, Ey, Hx, Hy, Hz 중 선택
   - 재생: 애니메이션으로 결과 확인

## 설정 저장/불러오기

- **저장**: "설정 저장" 버튼 → JSON 파일
- **불러오기**: "설정 불러오기" 버튼 → 이전 설정 복원

## 출력 폴더

- 기본값: `saves/` (프로젝트 내)
- 변경: 좌측 하단 "출력 경로"에서 선택

## 주요 기능

- **3D FDTD 시뮬레이션**: PML 경계, 광원, 재질 지원
- **유전율/투자율/감쇠율 제어**: 각 구조별 독립적 설정
- **실시간 진행 표시**: 시뮬레이션 중 진행률 모니터링
- **결과 시각화**: 전자파 필드의 시간 변화 확인
- **설정 저장**: JSON 형식으로 시뮬레이션 설정 보관

## 라이선스

MIT

##

Claude Sonnet 4.6을 이용해 작성되었습니다.
