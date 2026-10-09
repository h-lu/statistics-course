# V2题库约定

本地重设计当前只制作第1–8课：第5课使用 `lesson-v2r4-05.yml`、ID `v2-l05-r4`，第1–4、6–8课使用r3（第8课为 `v2-l08-r3`）。每课5组概念、A/B各5题。第9–32课尚未制作新课包，不出现在新建场次目录。生产实际版本仍以部署状态为准，本次未部署。

第9–32课已发布的v2初版与r1全部移入两处题库各自的 `archive/redesign-2026-10-09/`。题目文件名、lesson_id和字节不变；服务显式加载该历史目录，旧场次继续按原ID读取原题。完整归档与恢复见[归档说明](../../../archive/redesign-2026-10-09/README.md)。

## 格式

以下用r2示范格式；新增修订时同时更改文件名和lesson_id，不能覆盖既有题目。

```yaml
lesson_id: v2-lNN-r2
title: 第NN课 · 主题
duration_seconds:
  attempt_a: 300
  learn: 240
  attempt_b: 300
items:
  - concept_id: topic-id
    title: 规范概念名称
    tutor_context: 请AI用另一情境解释概念并提出问题。
    pair:
      a:
        prompt: 具体判断问题
        options:
          - {id: A, text: 选项一, misconception: null}
          - {id: B, text: 选项二, misconception: plausible-confusion-one}
          - {id: C, text: 选项三, misconception: plausible-confusion-two}
          - {id: D, text: 选项四, misconception: plausible-confusion-three}
        answer: A
        explanation: 解释概念、计算和错误选项混淆之处，不只重复字母。
      b:
        prompt: 同概念的不同情境或判断任务
        options:
          - {id: A, text: 选项一, misconception: plausible-confusion-one}
          - {id: B, text: 选项二, misconception: null}
          - {id: C, text: 选项三, misconception: plausible-confusion-two}
          - {id: D, text: 选项四, misconception: plausible-confusion-three}
        answer: B
        explanation: 给出判断依据与适用条件。
```

概念ID在课内唯一；四个选项ID固定A—D，每题只有一个正确项，其misconception为null。其余三项用具体错误类型标记，不只写“错误1”。正确字母在整套题中分散，但不能牺牲题目含义来追求机械分布。

题干面向初学者，使用规范术语和具体对象。计算题说明记录范围、单位、分母及阈值是否含等号；分位数题给出采用的约定。B不只是A换字母或数字；通过不同情境、反例或判断任务检查同一核心概念。当前页面按纯文本展示题干，不依赖Markdown表格、公式插件或外部链接才能作答。

## 两处副本与历史保护

教师目录中的每个题库，在`stat-check/app/question_bank/`的同一相对路径应有同名、逐字节相同的副本（包括历史子目录）。新增版本须同步两处，运行加载、数值核对和历史兼容测试。不要将答案复制进学生模板。

已发布的V1、`lesson-v2-NN.yml`、`lesson-v2r1-NN.yml`及以后发布的各修订版都不可原地改题。新版本使用新ID；旧场次按原lesson_id加载原题，保留答案、解释和历史作答含义。即使仅修正文案，也要新建版本；不同修订版的正确字母可能不同，不能把旧答案改按新题重新评分。

新建场次按课次选择已安装的最高数字修订号。当前新建场次目录仅列第1–8课；历史第9–32课仍可按原ID读取，不作为已制作课程。逐课升级保留其他已制作课次；r10高于r9，不按字母排序。版本目录变更不应修改当前场次。

## 审核与发布

核对题目与学生README、LEARN、报告要求及教师指导一致，逐题重算并检查唯一答案。格式测试不能证明干扰项有诊断价值，也不能证明A/B难度相当；真实试教后再观察阅读负担和错误分布。

先完成PR审阅，部署需另行安排。升级时保留数据库与原题库，避开正在作答或学习的场次；上线后为后续教学新建对应版本场次，不覆盖已有场次。评分仍以GRADING为准，前两课不计分，AI全过程可用。
