const STORAGE_KEY = "sql-quiz-progress";

let allQuestions = [];
let queue = [];
let currentIndex = 0;
let selected = new Set();
let answered = false;

const $ = (sel) => document.querySelector(sel);

function hashText(text) {
  let h = 0;
  const s = text.replace(/\s+/g, " ").trim();
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return String(h);
}

function dedupeQuestions(questions) {
  const seen = new Set();
  return questions.filter((q) => {
    const key = hashText(q.text);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function loadProgress() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || { done: [], correct: [] };
  } catch {
    return { done: [], correct: [] };
  }
}

function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

function updateHomeStats() {
  const progress = loadProgress();
  $("#total-count").textContent = allQuestions.length;
  $("#done-count").textContent = progress.done.length;
  $("#correct-count").textContent = progress.correct.length;
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $(id).classList.add("active");
}

function buildQueue(shuffle) {
  queue = dedupeQuestions([...allQuestions]);
  if (shuffle) {
    for (let i = queue.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [queue[i], queue[j]] = [queue[j], queue[i]];
    }
  }
  currentIndex = 0;
}

function renderQuestion() {
  if (currentIndex >= queue.length) {
    showScreen("#home-screen");
    updateHomeStats();
    alert("練習完成！");
    return;
  }

  const q = queue[currentIndex];
  selected.clear();
  answered = false;

  $("#quiz-index").textContent = `${currentIndex + 1} / ${queue.length}`;
  $("#progress-fill").style.width = `${((currentIndex + 1) / queue.length) * 100}%`;
  $("#question-text").textContent = q.text;

  const imgEl = $("#question-image");
  if (q.hasImage) {
    imgEl.classList.remove("hidden");
  } else {
    imgEl.classList.add("hidden");
  }

  const isMulti = q.multi || (q.answer && q.answer.includes(","));
  const list = $("#options-list");
  list.innerHTML = "";

  q.options.forEach((opt) => {
    const li = document.createElement("li");
    li.className = "option" + (isMulti ? " multi" : "");

    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = isMulti ? "checkbox" : "radio";
    input.name = "answer";
    input.value = opt.id;

    input.addEventListener("change", () => {
      if (answered) return;
      if (isMulti) {
        if (input.checked) selected.add(opt.id);
        else selected.delete(opt.id);
      } else {
        selected = new Set([opt.id]);
      }
      list.querySelectorAll("label").forEach((l) => l.classList.remove("selected"));
      list.querySelectorAll("input:checked").forEach((inp) => {
        inp.closest("label").classList.add("selected");
      });
      $("#btn-submit").disabled = selected.size === 0;
    });

    const letter = document.createElement("span");
    letter.className = "option-letter";
    letter.textContent = opt.id.toUpperCase() + ".";

    const text = document.createElement("span");
    text.className = "option-text";
    text.textContent = opt.text;

    label.append(input, letter, text);
    li.append(label);
    list.append(li);
  });

  $("#btn-submit").disabled = true;
  $("#btn-submit").classList.remove("hidden");
  $("#btn-next").classList.add("hidden");
  $("#feedback").classList.add("hidden");
}

function checkAnswer(q, chosen) {
  if (!q.answer) return null;
  const expected = new Set(q.answer.split(",").map((s) => s.trim()));
  const chosenSet = new Set(chosen);
  if (expected.size !== chosenSet.size) return false;
  for (const c of expected) {
    if (!chosenSet.has(c)) return false;
  }
  return true;
}

function highlightResults(q, chosen) {
  const expected = q.answer ? new Set(q.answer.split(",").map((s) => s.trim())) : new Set();
  document.querySelectorAll(".option input").forEach((input) => {
    const label = input.closest("label");
    const id = input.value;
    if (expected.has(id)) label.classList.add("correct");
    else if (chosen.has(id)) label.classList.add("wrong");
  });
}

function recordProgress(qid, isCorrect) {
  const progress = loadProgress();
  if (!progress.done.includes(qid)) progress.done.push(qid);
  if (isCorrect && !progress.correct.includes(qid)) progress.correct.push(qid);
  saveProgress(progress);
}

function submitAnswer() {
  if (answered || selected.size === 0) return;
  answered = true;

  const q = queue[currentIndex];
  const chosen = [...selected];
  const result = checkAnswer(q, chosen);
  const feedback = $("#feedback");

  highlightResults(q, selected);
  feedback.classList.remove("hidden", "correct", "wrong", "neutral");

  if (result === null) {
    feedback.classList.add("neutral");
    feedback.textContent = "此題暫無標準答案，請對照講義確認。";
    recordProgress(q.id, false);
  } else if (result) {
    feedback.classList.add("correct");
    feedback.textContent = "答對了！";
    recordProgress(q.id, true);
  } else {
    feedback.classList.add("wrong");
    const ansText = q.answer
      ? q.answer.toUpperCase().split(",").join("、")
      : "";
    feedback.textContent = `答錯了。正確答案：${ansText}`;
    recordProgress(q.id, false);
  }

  $("#btn-submit").classList.add("hidden");
  $("#btn-next").classList.remove("hidden");
  updateHomeStats();
}

function nextQuestion() {
  currentIndex++;
  renderQuestion();
}

async function loadQuizData() {
  if (window.QUIZ_DATA?.questions?.length) {
    return window.QUIZ_DATA;
  }
  const res = await fetch("questions.json");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function init() {
  try {
    const data = await loadQuizData();
    allQuestions = dedupeQuestions(data.questions);
    updateHomeStats();
  } catch (e) {
    $("#total-count").textContent = "載入失敗";
    document.querySelector(".hint").textContent =
      "無法載入題庫。請用本地伺服器開啟，或部署至 GitHub Pages。";
    console.error(e);
  }
}

$("#btn-random").addEventListener("click", () => {
  if (allQuestions.length === 0) return;
  buildQueue(true);
  showScreen("#quiz-screen");
  renderQuestion();
});

$("#btn-seq").addEventListener("click", () => {
  if (allQuestions.length === 0) return;
  buildQueue(false);
  showScreen("#quiz-screen");
  renderQuestion();
});

$("#btn-reset").addEventListener("click", () => {
  if (confirm("確定要重置所有練習進度？")) {
    localStorage.removeItem(STORAGE_KEY);
    updateHomeStats();
  }
});

$("#btn-back").addEventListener("click", () => {
  showScreen("#home-screen");
  updateHomeStats();
});

$("#btn-skip").addEventListener("click", nextQuestion);
$("#btn-submit").addEventListener("click", submitAnswer);
$("#btn-next").addEventListener("click", nextQuestion);

init();
