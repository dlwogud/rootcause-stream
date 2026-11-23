# 측정에 쓴 모델 버전

> 2026-11-23 확인. 출처: Claude Code 실행 기록(`~/.claude/projects/…rootcause-stream/*.jsonl`의 `message.model`)과
> `data/rootcause.db` 의 `eval_runs.started_at` 을 시각으로 맞춰 봤다.

## 요약

**발표자료·README 의 숫자는 모두 Claude 5.5 세대로 측정했다.**

| 역할 | 모델 | 비고 |
|---|---|---|
| 진단 (가설 · 도구 · 촬영 요청 · 결론) | **Sonnet 5.5** (`claude-sonnet-5-5`) | 비교 실험은 Haiku 5.5 로도 돌렸다 |
| 사진 판독 (VLM) | **Haiku 5.5** (`claude-haiku-5-5`) | 판독기 비교 한 번(#75)만 Sonnet 5.5 |
| 채점 (LLM-as-Judge) | **Opus 5.5** (`claude-opus-5-5`) | #50 까지는 Sonnet 5.5. Haiku·Sonnet 비교는 둘 다 Opus 로 다시 채점 |

Opus 는 채점에만 썼다. 진단에 Opus 를 쓴 측정은 없다.

## 버전이 바뀐 시점

코드는 `claude -p --model haiku|sonnet|opus` 처럼 **별칭**만 넘긴다. 별칭이 가리키는 버전은 Claude Code 가 정한다.
실행 기록상 **2026-11-17 14:17 ~ 14:28 (KST)** 사이에 4.x → 5.5 로 바뀌었다.

| 측정 | 시각 (KST) | 실제 모델 | 발표 숫자에 쓰였나 |
|---|---|---|---|
| #1 ~ #6 | 11/16 19:25 ~ 11/17 14:12 | Haiku 4.5, 채점 Sonnet 4.6 | 아니오 — 공장 데이터 숫자는 A #30~, B·C #56~ 부터만 쓴다 (`deck/export_numbers.py` `FROM_RUN`) |
| #7 ~ #8 | 11/17 14:17 ~ 14:28 | 4.x 와 5.5 가 섞임 | 아니오 — #7 은 Tier D(측정 불성립, `RESULTS_TIER_D.md`) |
| #9 ~ #84 | 11/17 14:41 ~ | **5.5** | 예 |

## 기록이 틀려 있던 것 (2026-11-23 수정)

- 채점 결과에 남은 채점 모델 이름(`_M1_judge`, `judge_model`)이 실제와 달랐다.
  - Sonnet·Opus 로 채점한 측정도 대부분 `claude-haiku-5-5` 로 적혀 있다.
  - 원인: Claude Code 는 호출마다 내부에서 Haiku 를 짧게 한 번 더 부르고, 응답의 `modelUsage` 에 그 Haiku 가 **맨 앞에** 온다. 실측 예: Sonnet 지정 시 Haiku 출력 24 토큰, Sonnet 출력 1,653 토큰. 코드가 첫 항목을 집었다.
  - **채점은 지정한 모델이 했다.** 기록만 틀렸다. 숫자는 바뀌지 않는다.
  - 고침: `app/agent/cli.py` `resolved_model` 이 지정한 별칭과 맞는 이름을 고른다. 판독기·baseline 기록도 같은 함수를 쓴다.
- 진단 루프(`app/agent/loop.py`)는 모델 이름을 아예 남기지 않았다.
  - 이제 `usage["models"]` 에 남는다.
  - 측정이 끝나면 `eval_runs.model_map` 의 `"resolved"` 에 역할별 실제 이름을 적는다.
- #84 이전 측정의 `model_map` 에는 별칭만 있다. 그 측정의 버전은 위 표로 판단한다.
