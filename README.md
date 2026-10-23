<p>
  <a href="https://mcas.uos.ac.kr"><img src="assets/mcaslab.png" alt="MCAS Lab" height="34"></a>
  &nbsp;&nbsp;
  <a href="https://www.uos.ac.kr"><img src="assets/uos.png" alt="University of Seoul" height="20"></a>
</p>

# LDO Census

ISSCC, VLSI, JSSC, CICC, ESSCIRC/ESSERC, A-SSCC, SSC-L, TCAS-I/II, TVLSI에 실린 LDO·선형 레귤레이터 논문을 모아 보여주는 사이트입니다. MCAS Lab(서울시립대학교 첨단융합학부)에서 운영합니다. 자매 사이트: [ADC Census](https://mixedcas-lab.github.io/adc-census/), [PLL Census](https://mixedcas-lab.github.io/pll-census/).

- 사이트: https://mixedcas-lab.github.io/ldo-census/
- 데이터 출처: IEEE Xplore API (서지 메타데이터와 링크만 공개, 초록·본문은 올리지 않음)

## 구성

```
index.html, app.js, style.css   사이트 (빌드 과정 없음, GitHub Pages가 그대로 서비스)
data/papers.json                LDO 논문 목록 (빌더가 생성)
data/meta.json                  갱신일, 범위, 집계
data/annotations.csv            검수 값 (사람이 편집)
collector/build.py              adc-census 캐시를 읽어 papers.json 생성 (Python 3.8+, 표준 라이브러리만)
collector/classify.py           LDO 판별, 유형(Analog/Digital/Hybrid)·구조·응용 태깅, 수치 추출 규칙
collector/venues.json           시작 연도, 캐시 위치, venue 매칭 규칙
scripts/update.sh               랩 서버 cron용: 재생성 → 커밋 → push
```

## 동작 방식

1. **데이터**: adc-census 수집기가 같은 학회·저널의 전체 논문을 랩 서버 캐시(`~/adc-census/cache/raw`)에 받아 둡니다. 이 저장소는 그 캐시를 읽기만 하므로 IEEE API를 따로 쓰지 않습니다. IEEE Access는 adc-census가 변환기 논문만 받기 때문에 제외했습니다.
2. **분류**: 제목에 LDO, low-dropout, linear regulator, capacitor-less regulator 등이 있으면 core입니다. 스위치드 커패시터·인덕터형 레귤레이터는 제외하고, 프로세서·SoC 안의 LDO나 초록에서만 언급한 논문은 related로 두고 수치를 표시하지 않습니다.
3. **수치**: 제목·초록에서 최대 부하전류, 정지전류(I<sub>Q</sub>), V<sub>IN</sub>/V<sub>OUT</sub>, dropout, PSRR(주파수), 부하 과도 droop, settling time, C<sub>OUT</sub>, 전류 효율, FoM, 전류 밀도, 공정, 면적을 정규식으로 뽑습니다. FoM = C<sub>OUT</sub>·ΔV<sub>OUT</sub>·I<sub>Q</sub>/I<sub>L,max</sub><sup>2</sup>(Hazucha, JSSC 2005)이며, 논문에 없으면 뽑은 값으로 계산합니다(≈ 표시).
4. **공개**: cron이 매일 06:52(adc-census 06:17 갱신 뒤) 재생성하고, 바뀐 것이 있으면 커밋·push합니다.

## 그래프

Chart 메뉴: I<sub>Q</sub> vs. I<sub>L,max</sub>(전류 효율 99~99.999% 등고선), FoM 연도별 추세, FoM vs. I<sub>L,max</sub>, droop vs. I<sub>L,max</sub>, PSRR vs. 주파수, Custom(x·y축 직접 선택, log 전환).

## 수치 수정 요청

각 논문 아래 **Report a fix**를 누르면 논문 id, 현재 값, annotations.csv 행 형식이 채워진 GitHub 이슈가 열립니다. 연구실은 확인해 `data/annotations.csv`에 반영합니다.

| 열 | 내용 |
|---|---|
| `id` | IEEE article number (Xplore 주소 끝의 숫자) |
| `exclude` | `1`이면 목록에서 제외 |
| `type` | `Analog`, `Digital`, `Hybrid` |
| `arch`, `app` | 여러 개면 `;`로 구분 (예: `Capacitor-less;FVF`) |
| `il`, `iq` | A (`100m`, `14u`, `54n`) |
| `vin`, `vout`, `vdo`, `dv` | V (`150m`) |
| `psrr`, `psrr_f` | dB(음수), Hz |
| `ts`, `cout`, `fom` | s, F, s |
| `ce`, `node`, `area` | %, nm, mm² |
| `cal`, `note`, `by` | 보정 여부, 메모, 검수자 (`by`에 AI 도구 이름이면 AI 추출로 표시) |

빈칸은 자동 값을 유지하고, `-`나 `NA`는 값을 지웁니다.

## 참고

- IEEE Xplore API 이용약관을 따릅니다. 초록과 본문은 공개하지 않고, 서지 정보와 Xplore 링크만 제공합니다.
- 자동 추출 수치는 오류가 있을 수 있습니다. 인용·비교 전에 원문을 확인하세요.
