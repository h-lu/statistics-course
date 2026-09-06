# V2题库约定

文件`lesson-v2r1-NN.yml`，课次ID`v2-lNN-r1`，标题`第NN课 · 主题`。32套，每套5个概念，各含a/b两道四选一题。

```yaml
lesson_id: v2-lNN-r1
title: 第NN课 · 主题
duration_seconds:
  attempt_a: 300
  learn: 240
  attempt_b: 300
items:
  - concept_id: topic-id
    title: 规范概念名称
    tutor_context: 请AI用另一情境解释概念并提出问题，不索取原题答案。
    pair:
      a:
        prompt: 具体判断问题
        options:
          - {id: A, text: 选项一, misconception: null}
          - {id: B, text: 选项二, misconception: plausible-confusion}
          - {id: C, text: 选项三, misconception: plausible-confusion}
          - {id: D, text: 选项四, misconception: plausible-confusion}
        answer: A
        explanation: 解释概念含义与适用条件，不只重复字母。
      b:
        prompt: 同概念的不同情境问题
        options:
          - {id: A, text: 选项一, misconception: plausible-confusion}
          - {id: B, text: 选项二, misconception: null}
          - {id: C, text: 选项三, misconception: plausible-confusion}
          - {id: D, text: 选项四, misconception: plausible-confusion}
        answer: B
        explanation: 给出判断依据。
```

概念ID在课内唯一；四个选项ID固定A—D，正确字母在一套题中分散。B不只是A换字母；错项应具有诊断意义。`legacy/`和已发布的`lesson-v2-NN.yml`不可覆盖，旧ID继续关联原题目和历史答案；新版本变更题义时使用新ID而非原地覆盖。
