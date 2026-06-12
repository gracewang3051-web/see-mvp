const state = {
  dealer: null,
  imageFile: null,
  imageDataUrl: "",
  lastMatches: [],
  reportDraft: null
};

const $ = (id) => document.getElementById(id);

const sampleInput = `十指指纹采集记录：用户在视觉和逻辑空间任务中反应较快，面对家庭沟通时更关注情绪感受。最近处在职业选择阶段，希望了解自己的优势学习通道、压力下的决策方式，以及如何把先天特质转化为成长行动。`;

function init() {
  const dealers = window.SEE_DEMO.dealers;
  const params = new URLSearchParams(window.location.search);
  const dealerId = params.get("dealer") || dealers[0].id;
  state.dealer = dealers.find((item) => item.id === dealerId) || dealers[0];

  renderDealers();
  renderDealerProfile();
  renderKnowledgeStack();
  renderEmptyReport();
  bindEvents();
}

function bindEvents() {
  $("imageInput").addEventListener("change", onImageSelected);
  $("runOcrBtn").addEventListener("click", runOcr);
  $("sampleBtn").addEventListener("click", () => {
    $("ocrText").value = sampleInput;
    $("ocrStatus").textContent = "已载入样例";
  });
  $("generateBtn").addEventListener("click", generateTextReport);
  $("graphicBtn").addEventListener("click", generateGraphicReport);
}

function renderDealers() {
  $("dealerList").innerHTML = window.SEE_DEMO.dealers
    .map((dealer) => {
      const active = dealer.id === state.dealer.id ? "active" : "";
      return `<button class="dealer-card ${active}" data-id="${dealer.id}">
        <strong>${dealer.name}</strong>
        <span>${dealer.role} · ${dealer.city}</span>
      </button>`;
    })
    .join("");

  document.querySelectorAll(".dealer-card").forEach((button) => {
    button.addEventListener("click", () => {
      state.dealer = window.SEE_DEMO.dealers.find((item) => item.id === button.dataset.id);
      renderDealers();
      renderDealerProfile();
      renderKnowledgeStack();
      renderEmptyReport();
    });
  });
}

function renderDealerProfile() {
  $("dealerProfile").innerHTML = `
    <div class="avatar">${state.dealer.initials}</div>
    <h2>${state.dealer.name}</h2>
    <p>${state.dealer.role}</p>
    <small>${state.dealer.intro}</small>
    <small>${state.dealer.city} · ${state.dealer.phone}</small>
  `;
  $("entryTitle").textContent = `${state.dealer.name}的 SEE 定制入口`;
  $("entryChip").textContent = `扫码入口 /entry/${state.dealer.id}`;
}

function renderKnowledgeStack() {
  $("knowledgeStack").innerHTML = state.dealer.stack.map((item) => `<span class="kb-pill">${item}</span>`).join("");
}

function renderEmptyReport() {
  state.reportDraft = null;
  $("draftText").value = "";
  $("reportPreview").innerHTML = `
    <div class="report-cover">
      <h2>等待生成 SEE 生命印迹报告</h2>
      <p>上传照片并完成 OCR 后，这里会生成带经销商信息的网页报告。</p>
    </div>
    <div class="report-body">
      <section class="report-section">
        <h3>DEMO 流程</h3>
        <p>照片输入会先转成文字，再对照知识库生成文字报告草稿，最后套用模板生成图文报告。</p>
      </section>
    </div>
  `;
  $("retrievalLog").innerHTML = `<div class="log-item"><strong>尚未调用</strong><p>生成报告后会显示命中的知识库片段。</p></div>`;
}

async function onImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  state.imageFile = file;
  state.imageDataUrl = await readFileAsDataUrl(file);
  $("imagePreview").innerHTML = `<img src="${state.imageDataUrl}" alt="上传的照片预览" />`;
  $("ocrStatus").textContent = "图片已选择";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function runOcr() {
  if (!state.imageFile) {
    $("ocrStatus").textContent = "请先选择照片";
    return;
  }

  const button = $("runOcrBtn");
  button.disabled = true;
  $("ocrStatus").textContent = "正在识别...";
  try {
    const result = await Tesseract.recognize(state.imageFile, "chi_sim+eng", {
      logger: (message) => {
        if (message.status === "recognizing text") {
          $("ocrStatus").textContent = `识别中 ${Math.round(message.progress * 100)}%`;
        }
      }
    });
    $("ocrText").value = result.data.text.trim();
    $("ocrStatus").textContent = "识别完成";
  } catch (error) {
    $("ocrStatus").textContent = "识别失败，可手动粘贴";
  } finally {
    button.disabled = false;
  }
}

function generateTextReport() {
  const input = $("ocrText").value.trim();
  const customerName = $("customerName").value.trim() || "体验用户";
  const scenario = $("scenario").value;
  const familyRoles = $("familyRoles").value.trim() || "妈妈、爸爸、女儿";
  const matches = retrieveKnowledge(input + " " + scenario);
  state.lastMatches = matches;

  const profile = inferProfile(input, scenario);
  state.reportDraft = buildTextDraft({ input, customerName, scenario, matches, profile, familyRoles });
  $("draftText").value = JSON.stringify(state.reportDraft, null, 2);
  renderRetrievalLog(matches);
  $("reportPreview").innerHTML = `
    <div class="report-cover">
      <h2>文字报告草稿已生成</h2>
      <p>请先检查中间的草稿内容，必要时修改文字，再点击“生成图文报告”。</p>
    </div>
    <div class="report-body">
      <section class="report-section">
        <h3>当前流程</h3>
        <p>已完成信息读取、知识库对照和文字报告草稿生成。图文模板会读取这份草稿，而不是重新凭空生成内容。</p>
      </section>
    </div>
  `;
}

function generateGraphicReport() {
  const customerName = $("customerName").value.trim() || "体验用户";
  const scenario = $("scenario").value;
  const reportTemplate = $("reportTemplate").value;
  const familyRoles = $("familyRoles").value.trim() || "妈妈、爸爸、女儿";
  const input = $("ocrText").value.trim();
  const matches = state.lastMatches.length ? state.lastMatches : retrieveKnowledge(input + " " + scenario);
  const profile = inferProfile(input, scenario);
  const draft = readDraftFromEditor() || buildTextDraft({ input, customerName, scenario, matches, profile, familyRoles });

  state.reportDraft = draft;
  const report =
    reportTemplate === "lifeTree"
      ? buildLifeTreeReport({ customerName, scenario, matches, profile, familyRoles, draft })
      : buildFamilyBrainReport({ customerName, scenario, matches, profile, familyRoles, draft });
  $("reportPreview").innerHTML = report;
  renderRetrievalLog(matches);
}

function readDraftFromEditor() {
  try {
    return JSON.parse($("draftText").value);
  } catch (error) {
    $("draftText").value = `${$("draftText").value}\n\n【提示】草稿 JSON 格式有误，已使用系统重新生成的草稿渲染图文报告。`;
    return null;
  }
}

function buildTextDraft({ input, customerName, scenario, matches, profile, familyRoles }) {
  const roles = familyRoles.split(/[、,，\s]+/).filter(Boolean);
  const [roleA = "妈妈", roleB = "爸爸", roleC = "女儿", roleD = "二女儿"] = roles;
  const knowledgeTitles = matches.map((item) => item.title);

  return {
    meta: {
      customerName,
      scenario,
      dealerName: state.dealer.name,
      generatedAt: new Date().toLocaleDateString("zh-CN"),
      sourceSummary: input || "使用样例输入生成"
    },
    knowledgeMatch: knowledgeTitles,
    coreInsight: profile.lead,
    familyBrain: {
      title: "家庭大脑偏好及成长建议",
      subtitle: "把一家人的差异，看成一套可以互相支持的系统。",
      roles: [
        {
          name: roleA,
          label: "家庭的方向盘",
          preference: "方向",
          advantage: "擅长行动规划、判断和推进。",
          risk: "标准高和推进快时，可能让家人感到压力。"
        },
        {
          name: roleB,
          label: "家庭的执行力",
          preference: "行动",
          advantage: "愿意为家付出，也很能做事。",
          risk: "关键不是少做，而是行动前先确认边界。"
        },
        {
          name: roleC,
          label: "家庭的感受雷达",
          preference: "感受",
          advantage: "很在意语气、节奏和表达方式，适合用图像、故事和手作表达。",
          risk: "语气一重，内容就很难进入。"
        }
      ],
      signalPrinciple: "冲突常常不是不爱，而是表达方式和接收方式不同。",
      communicationFocus: ["事情有没有推进", "我有没有被理解"],
      formulas: [
        "我现在是开心/不开心地跟你说。",
        "我需要你安慰我，不是马上给建议。",
        "你想自己选，还是我帮你定？"
      ],
      growthPath: [
        "学习方式：先固定一条清晰路线，再扩展更多方法。",
        "老师形态：老师的表达方式会影响她能否接收知识。",
        "表达训练：从低压力表达开始，先讲故事、复述情节或介绍作品。",
        "天赋探索：重点观察视觉表达和创意工具。"
      ],
      finalAdvice: "少一点猜，多一点明说；少一点评价，多一点确认；少一点急着改变对方，多一点先看见对方。"
    },
    lifeTree: {
      title: "家族生命树 · 你的专属成长图谱",
      selfLabel: roleA === "你" ? "你" : customerName,
      crown: "圆满的自我",
      tags: ["知行合一", "内耗消解", "完整自洽"],
      root: "高维处理器 · 意识内核",
      coreIssue: "打破“想得多做得少”的内耗",
      branches: [
        {
          name: "伴侣",
          trait: "逆向破执 · 行动引擎",
          headline: "打破你的“爱较真”和“过度内耗”",
          advice: "用行动代替辩论，教你停止纠结，直接落地。"
        },
        {
          name: roleB || "小儿子",
          trait: "闭环执行 · 目标落地",
          headline: "用超强行动力，补全你“想多做少”的短板",
          advice: "教你少说多做，用行动闭环完成目标。"
        },
        {
          name: roleC || "大女儿",
          trait: "思维显化 · 行动示范",
          headline: "把你的内在思考“外化”，示范行动力",
          advice: "教你放下大道理，把复杂想法变成简单行动。"
        },
        {
          name: roleD || "二女儿",
          trait: "接纳包容 · 耐心试炼",
          headline: "照见你“行动力不足”的课题，教你接纳不完美",
          advice: "让你学会接纳“暂时做不到”，放下对高效的执念。"
        }
      ],
      footer: "家人从不是纷扰，而是托举你成长的养分，让你从“想得多”走向“做得成”。"
    }
  };
}

function retrieveKnowledge(query) {
  const keywords = query
    .replace(/[，。；：、,.!?]/g, " ")
    .split(/\s+/)
    .filter((item) => item.length >= 2);

  return window.SEE_DEMO.knowledge
    .map((item) => {
      const haystack = `${item.title} ${item.text} ${item.source}`;
      const score = keywords.reduce((sum, word) => sum + (haystack.includes(word) ? 1 : 0), 0);
      const sceneBonus = haystack.includes($("scenario").value) ? 2 : 0;
      return { ...item, score: score + sceneBonus };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);
}

function inferProfile(input, scenario) {
  const text = input || sampleInput;
  const hasVisual = /视觉|图像|照片|观察|颜色|空间/.test(text);
  const hasLogic = /逻辑|分析|数据|结构|决策|职业/.test(text);
  const hasEmotion = /情绪|感受|关系|家庭|沟通|亲子/.test(text);
  const hasStress = /压力|焦虑|纠结|选择|困难|高负荷/.test(text);

  return {
    a: hasLogic ? 76 : 58,
    b: hasEmotion ? 68 : 46,
    c: hasStress ? 64 : 39,
    d: hasStress ? 28 : 16,
    lead:
      scenario === "团队配置"
        ? "适合在结构化分工中发挥优势，同时需要明确协作边界。"
        : hasEmotion
          ? "理性判断与情绪感知同时被调动，适合从关系场景进入觉察。"
          : "当前更容易从结构分析和目标拆解进入自我理解。",
    visual: hasVisual,
    logic: hasLogic,
    emotion: hasEmotion,
    stress: hasStress
  };
}

function buildFamilyBrainReport({ customerName, scenario, matches, profile, familyRoles, draft }) {
  const dealer = state.dealer;
  const knowledgeLine = (draft.knowledgeMatch || matches.map((item) => item.title)).join("、");
  const brain = draft.familyBrain || {};
  const roles = brain.roles || [];
  const roleA = roles[0] || { name: "妈妈", preference: "方向", label: "家庭的方向盘", advantage: "擅长行动规划、判断和推进。", risk: "标准高和推进快时，可能让家人感到压力。" };
  const roleB = roles[1] || { name: "爸爸", preference: "行动", label: "家庭的执行力", advantage: "愿意为家付出，也很能做事。", risk: "关键不是少做，而是行动前先确认边界。" };
  const roleC = roles[2] || { name: "女儿", preference: "感受", label: "家庭的感受雷达", advantage: "很在意语气、节奏和表达方式。", risk: "语气一重，内容就很难进入。" };
  const formulas = brain.formulas || [];
  const growthPath = brain.growthPath || [];

  return `
    <article class="poster poster-brain">
      <header class="brain-hero">
        <div>
          <span class="soft-label">陪玩成长图</span>
          <h2>${brain.title || "家庭大脑偏好及成长建议"}</h2>
          <p>${brain.subtitle || "把一家人的差异，看成一套可以互相支持的系统。"}</p>
          <small>${customerName} · ${scenario} · ${dealer.name}定制入口</small>
        </div>
        <div class="triad">
          <div class="triad-node node-top"><strong>${roleA.name}</strong><span>${roleA.preference}</span></div>
          <div class="triad-node node-left"><strong>${roleB.name}</strong><span>${roleB.preference}</span></div>
          <div class="triad-node node-right"><strong>${roleC.name}</strong><span>${roleC.preference}</span></div>
          <span class="triad-word">互补</span>
        </div>
      </header>

      <section class="poster-section">
        <div class="section-num">01</div>
        <div class="section-copy">
          <h3>三个人，不是三种问题，而是三种优势</h3>
          <p>${roleA.name}给${roleA.preference}，${roleB.name}给${roleB.preference}，${roleC.name}给${roleC.preference}和创造力。</p>
        </div>
        <div class="role-card-grid">
          <div class="role-card green"><span>◉</span><h4>${roleA.name}：${roleA.label}</h4><p>${roleA.advantage} 需要留意的是，${roleA.risk}</p></div>
          <div class="role-card blue"><span>⚙</span><h4>${roleB.name}：${roleB.label}</h4><p>${roleB.advantage} ${roleB.risk}</p></div>
          <div class="role-card coral"><span>♥</span><h4>${roleC.name}：${roleC.label}</h4><p>${roleC.advantage} ${roleC.risk}</p></div>
        </div>
      </section>

      <section class="poster-section split-section">
        <div class="section-num">02</div>
        <div class="section-copy">
          <h3>底层原理：家里需要换一套“信号语言”</h3>
          <p>${brain.signalPrinciple || "冲突常常不是不爱，而是表达方式和接收方式不同。"}</p>
        </div>
        <div class="quote-box">
          <small>${roleA.name}更容易关注</small>
          <strong>${(brain.communicationFocus || [])[0] || "事情有没有推进"}</strong>
          <small>${roleB.name}和${roleC.name}更容易关注</small>
          <strong>${(brain.communicationFocus || [])[1] || "我有没有被理解"}</strong>
          <p>所以，家庭沟通的重点不是讲更多道理，而是让彼此的信号能被接收到。</p>
        </div>
        <div class="signal-list">
          <div><strong>先降语气</strong><p>尤其对${roleC.name}，语气一重，内容就很难进入。</p></div>
          <div><strong>情绪明说</strong><p>不要只问事情，可以直接说“我刚刚有点委屈”。</p></div>
          <div><strong>行动前确认</strong><p>帮忙前先问边界，能减少很多好心办坏事。</p></div>
        </div>
      </section>

      <section class="poster-section">
        <div class="section-num">03</div>
        <div class="section-copy">
          <h3>三句家庭公式，替代反复解释和互相猜测</h3>
          <p>这些话经常用起来，起码能减少一半误解。</p>
        </div>
        <div class="formula-grid">
          <div><span>表达情绪</span><strong>“${formulas[0] || "我现在是开心/不开心地跟你说。"}”</strong></div>
          <div><span>表达感受</span><strong>“${formulas[1] || "我需要你安慰我，不是马上给建议。"}”</strong></div>
          <div><span>表达选择压力</span><strong>“${formulas[2] || "你想自己选，还是我帮你定？"}”</strong></div>
        </div>
      </section>

      <section class="poster-section">
        <div class="section-num">04</div>
        <div class="section-copy">
          <h3>${roleC.name}的成长路线：少而深，慢慢长出来</h3>
          <p>她需要的不是被催成外向高效，而是在稳定支持里发展深度和创造力。</p>
        </div>
        <div class="growth-grid">
          ${growthPath.map((item, index) => {
            const [title, text] = item.split("：");
            return `<div><b>${index + 1}</b><strong>${title || "成长建议"}</strong><p>${text || item}</p></div>`;
          }).join("")}
        </div>
      </section>

      <footer class="brain-advice">
        <h3>最后的核心建议</h3>
        <strong>${brain.finalAdvice || "少一点猜，多一点明说；少一点评价，多一点确认；少一点急着改变对方，多一点先看见对方。"}</strong>
        <p>本次调用知识库：${knowledgeLine}。${dealer.name} · ${dealer.phone}</p>
      </footer>
    </article>
  `;
}

function buildLifeTreeReport({ customerName, scenario, matches, profile, familyRoles, draft }) {
  const dealer = state.dealer;
  const tree = draft.lifeTree || {};
  const branches = tree.branches || [];
  const branchLeft = branches[0] || { name: "伴侣", trait: "逆向破执 · 行动引擎", headline: "打破你的“爱较真”和“过度内耗”", advice: "用行动代替辩论，教你停止纠结，直接落地。" };
  const branchOne = branches[1] || { name: "小儿子", trait: "闭环执行 · 目标落地", headline: "用超强行动力，补全你“想多做少”的短板", advice: "教你少说多做，用行动闭环完成目标。" };
  const branchTwo = branches[2] || { name: "大女儿", trait: "思维显化 · 行动示范", headline: "把你的内在思考“外化”，示范行动力", advice: "教你放下大道理，把复杂想法变成简单行动。" };
  const branchThree = branches[3] || { name: "二女儿", trait: "接纳包容 · 耐心试炼", headline: "照见你“行动力不足”的课题，教你接纳不完美", advice: "让你学会接纳“暂时做不到”，放下对高效的执念。" };
  const tags = tree.tags || ["知行合一", "内耗消解", "完整自洽"];

  return `
    <article class="poster poster-tree">
      <header class="tree-title">
        <h2>${tree.title || "家族生命树 · 你的专属成长图谱"}</h2>
        <p>${scenario} · ${dealer.name}定制入口 · ${new Date().toLocaleDateString("zh-CN")}</p>
      </header>

      <section class="tree-stage">
        <div class="tree-core">
          <div class="leaf-crown">
            <span>${tree.selfLabel || customerName}</span>
            <strong>${tree.crown || "圆满的自我"}</strong>
            ${tags.map((tag) => `<em>${tag}</em>`).join("")}
          </div>
          <div class="tree-trunk">知行合一<br />的进化之路</div>
          <div class="tree-root">
            <strong>${customerName}</strong>
            <span>${tree.root || "高维处理器 · 意识内核"}</span>
          </div>
        </div>

        <div class="tree-branch branch-left">
          <h3>${branchLeft.name}｜${branchLeft.trait}</h3>
          <strong>${branchLeft.headline}</strong>
          <p>${branchLeft.advice}</p>
        </div>

        <div class="tree-branch branch-one">
          <h3>${branchOne.name}｜${branchOne.trait}</h3>
          <strong>${branchOne.headline}</strong>
          <p>${branchOne.advice}</p>
        </div>

        <div class="tree-branch branch-two">
          <h3>${branchTwo.name}｜${branchTwo.trait}</h3>
          <strong>${branchTwo.headline}</strong>
          <p>${branchTwo.advice}</p>
        </div>

        <div class="tree-branch branch-three">
          <h3>${branchThree.name}｜${branchThree.trait}</h3>
          <strong>${branchThree.headline}</strong>
          <p>${branchThree.advice}</p>
        </div>
      </section>

      <footer class="tree-footer">
        <div>
          <span>高精神愿景</span>
          <span>逆向发散思维</span>
          <span>高共情听觉</span>
        </div>
        <strong>核心课题：${tree.coreIssue || "打破“想得多做得少”的内耗"}</strong>
        <p>${tree.footer || "家人从不是纷扰，而是托举你成长的养分，让你从“想得多”走向“做得成”。"}</p>
      </footer>
    </article>
  `;
}

function renderRetrievalLog(matches) {
  $("retrievalLog").innerHTML = matches
    .map(
      (item) => `<div class="log-item">
        <strong>${item.title}</strong>
        <p>${item.source}</p>
        <p>${item.text}</p>
      </div>`
    )
    .join("");
}

init();
