const h5State = {
  dealerIndex: 0,
  dealer: null,
  imageFile: null,
  matches: [],
  draft: null
};

const h5Sample = `十指指纹采集记录：用户在视觉和逻辑空间任务中反应较快，面对家庭沟通时更关注情绪感受。最近希望了解自己的优势学习通道、压力下的决策方式，以及如何把先天特质转化为成长行动。`;
const qs = (id) => document.getElementById(id);

function bootH5() {
  h5State.dealer = window.SEE_DEMO.dealers[0];
  renderDealer();
  showScreen("entryScreen");
  bindH5();
}

function bindH5() {
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => showScreen(button.dataset.go));
  });
  qs("dealerSwitchBtn").addEventListener("click", switchDealer);
  qs("h5ImageInput").addEventListener("change", selectImage);
  qs("h5OcrBtn").addEventListener("click", runH5Ocr);
  qs("h5SampleBtn").addEventListener("click", () => {
    qs("h5OcrText").value = h5Sample;
  });
  qs("h5DraftBtn").addEventListener("click", createDraft);
  qs("h5GraphicBtn").addEventListener("click", createGraphic);
}

function showScreen(id) {
  document.querySelectorAll(".hero-screen, .step-screen").forEach((item) => item.classList.remove("active"));
  qs(id).classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchDealer() {
  h5State.dealerIndex = (h5State.dealerIndex + 1) % window.SEE_DEMO.dealers.length;
  h5State.dealer = window.SEE_DEMO.dealers[h5State.dealerIndex];
  renderDealer();
}

function renderDealer() {
  const dealer = h5State.dealer;
  qs("dealerCard").innerHTML = `
    <div class="dealer-avatar-h5">${dealer.initials}</div>
    <div>
      <strong>${dealer.name}</strong>
      <p>${dealer.role} · ${dealer.city}</p>
      <p>${dealer.intro}</p>
    </div>
  `;
}

async function selectImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  h5State.imageFile = file;
  const url = await readAsDataUrl(file);
  qs("h5ImagePreview").innerHTML = `<img src="${url}" alt="上传照片" />`;
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function runH5Ocr() {
  if (!h5State.imageFile) {
    qs("h5OcrText").value = "请先上传照片，或点击样例输入。";
    return;
  }
  qs("h5OcrBtn").textContent = "识别中...";
  qs("h5OcrBtn").disabled = true;
  try {
    const result = await Tesseract.recognize(h5State.imageFile, "chi_sim+eng");
    qs("h5OcrText").value = result.data.text.trim();
  } catch (error) {
    qs("h5OcrText").value = "OCR 识别失败，请手动粘贴文字。";
  } finally {
    qs("h5OcrBtn").textContent = "OCR 识别";
    qs("h5OcrBtn").disabled = false;
  }
}

function createDraft() {
  const input = qs("h5OcrText").value.trim() || h5Sample;
  const scenario = qs("h5Scenario").value;
  const customerName = qs("h5CustomerName").value.trim() || "体验用户";
  const familyRoles = qs("h5FamilyRoles").value.trim() || "妈妈、爸爸、女儿";
  h5State.matches = retrieveH5Knowledge(`${input} ${scenario}`);
  h5State.draft = buildH5Draft({ input, scenario, customerName, familyRoles, matches: h5State.matches });
  qs("h5DraftText").value = JSON.stringify(h5State.draft, null, 2);
  showScreen("draftScreen");
}

function retrieveH5Knowledge(query) {
  const words = query
    .replace(/[，。；：、,.!?]/g, " ")
    .split(/\s+/)
    .filter((word) => word.length >= 2);
  return window.SEE_DEMO.knowledge
    .map((item) => {
      const text = `${item.source} ${item.title} ${item.text}`;
      return { ...item, score: words.reduce((sum, word) => sum + (text.includes(word) ? 1 : 0), 0) };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);
}

function buildH5Draft({ input, scenario, customerName, familyRoles, matches }) {
  const roles = familyRoles.split(/[、,，\s]+/).filter(Boolean);
  const [a = "妈妈", b = "爸爸", c = "女儿", d = "二女儿"] = roles;
  return {
    meta: {
      customerName,
      scenario,
      dealerName: h5State.dealer.name,
      sourceSummary: input
    },
    knowledgeMatch: matches.map((item) => item.title),
    familyBrain: {
      title: "家庭大脑偏好及成长建议",
      subtitle: "把一家人的差异，看成一套可以互相支持的系统。",
      roles: [
        { name: a, label: "家庭的方向盘", preference: "方向", text: "擅长规划和推进，需要留意语气与节奏。" },
        { name: b, label: "家庭的执行力", preference: "行动", text: "愿意付出和落地，需要先确认边界。" },
        { name: c, label: "家庭的感受雷达", preference: "感受", text: "在意语气和表达方式，适合用图像、故事、手作表达。" }
      ],
      finalAdvice: "少一点猜，多一点明说；少一点评价，多一点确认；先看见差异，再练习表达。"
    },
    lifeTree: {
      title: "家族生命树 · 你的专属成长图谱",
      self: customerName,
      crown: "圆满的自我",
      coreIssue: "打破“想得多做得少”的内耗",
      branches: [
        { name: "伴侣", text: "逆向破执 · 行动引擎，用行动代替辩论。" },
        { name: b || "小儿子", text: "闭环执行 · 目标落地，补全行动短板。" },
        { name: c || "大女儿", text: "思维显化 · 行动示范，把内在思考外化。" },
        { name: d || "二女儿", text: "接纳包容 · 耐心试炼，练习接纳不完美。" }
      ]
    }
  };
}

function createGraphic() {
  const draft = readH5Draft();
  const template = qs("h5Template").value;
  if (!draft) return;
  h5State.draft = draft;
  qs("h5ReportOutput").innerHTML = template === "lifeTree" ? renderLifeTree(draft) : renderFamilyBrain(draft);
  renderKnowledge();
  showScreen("reportScreen");
}

function readH5Draft() {
  try {
    return JSON.parse(qs("h5DraftText").value);
  } catch (error) {
    alert("文字报告草稿格式需要保持 JSON 结构。");
    return null;
  }
}

function renderFamilyBrain(draft) {
  const brain = draft.familyBrain;
  return `
    <article class="h5-poster">
      <p class="kicker">SEE 图文报告</p>
      <h3>${brain.title}</h3>
      <p>${brain.subtitle}</p>
      ${brain.roles
        .map(
          (role) => `<div class="h5-role"><strong>${role.name} · ${role.preference}</strong><p>${role.label}：${role.text}</p></div>`
        )
        .join("")}
      <div class="h5-final">${brain.finalAdvice}</div>
    </article>
  `;
}

function renderLifeTree(draft) {
  const tree = draft.lifeTree;
  return `
    <article class="h5-tree">
      <h3>${tree.title}</h3>
      <div class="tree-simple">
        <div class="crown">${tree.self}<br /><strong>${tree.crown}</strong></div>
        <div class="trunk"></div>
      </div>
      <div class="tree-note note-left"><strong>${tree.branches[0].name}</strong><p>${tree.branches[0].text}</p></div>
      <div class="tree-note note-one"><strong>${tree.branches[1].name}</strong><p>${tree.branches[1].text}</p></div>
      <div class="tree-note note-two"><strong>${tree.branches[2].name}</strong><p>${tree.branches[2].text}</p></div>
      <div class="h5-final" style="position:absolute;left:28px;right:28px;bottom:24px;">核心课题：${tree.coreIssue}</div>
    </article>
  `;
}

function renderKnowledge() {
  qs("h5KnowledgeLog").innerHTML = `
    <h3>知识库调用</h3>
    ${h5State.matches
      .map((item) => `<div><strong>${item.title}</strong><p>${item.source} · ${item.text}</p></div>`)
      .join("")}
  `;
}

bootH5();
