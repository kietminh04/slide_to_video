      }
    };

    async function generateSceneWithAI(chKey) {
      showLoading("??ang D??ng AI Vi???t L???i Tho???i...", "??ang ?????i chu???n ng??n s??ch t??? v?? t??nh to??n ng??? ??i???u s?? ph???m...");
      try {
        const res = await generateSceneWithAIInternal(chKey);
        hideLoading();
        renderScriptDocument();
        renderTimeline();
        if (res && res.isLiveAI) {
          const mName = LLMClient.getConfig().model || 'Live AI';
          showToast(`??? ???? sinh l???i tho???i AI cho ph??n c???nh t??? [${mName}]!`);
        } else {
          showToast("??? ???? sinh k???ch b???n s?? ph???m chuy??n s??u cho ph??n c???nh (B??? sinh CIKM C???c B???)!");
        }
      } catch (err) {
        hideLoading();
        console.error("L???i sinh l???i tho???i:", err);
        await showCustomAlert({
          title: "Ch??a Th??? Sinh L???i Tho???i",
          subtitle: "L???i k???t n???i",
          message: `Kh??ng th??? ho??n t???t sinh l???i tho???i: ${err.message}`,
          icon: "??????",
          buttonText: "???? Hi???u"
        });
      }
    }

    async function generateSceneWithAIInternal(chKey) {
      const allSources = activeProject.sources || [
        { name: activeProject.title + '.pdf', pages: 35, size: '1.2 MB', active: true }
      ];
      const activeSources = allSources.filter(s => s.active !== false);

      let targetItem = null;
      let targetSceneMatch = null;

      for (let sIdx = 0; sIdx < activeSources.length; sIdx++) {
        const src = activeSources[sIdx];
        const originalIdx = allSources.indexOf(src);
        const rootKey = getSourceKey(src, originalIdx >= 0 ? originalIdx : sIdx);
        const sourceScenes = (src.scenes && src.scenes.length > 0)
          ? src.scenes
          : (originalIdx === 0 ? currentScenes : []);
        const hierarchyChapters = getProjectHierarchy(activeProject, sourceScenes, src, originalIdx >= 0 ? originalIdx : sIdx);

        for (let chIdx = 0; chIdx < hierarchyChapters.length; chIdx++) {
          const currentKey = `ch-${rootKey}-${chIdx}`;
          if (currentKey === chKey) {
            targetItem = hierarchyChapters[chIdx];
            targetSceneMatch = (originalIdx === 0 ? currentScenes : (src.scenes || []))[chIdx];
            break;
          }
        }
        if (targetItem) break;
      }

      if (!targetItem) {
        throw new Error(`Kh??ng t??m th???y d??? li???u ph??n c???nh [${chKey}]`);
      }

      let purifiedText = '';
      let isLiveAI = false;

      // TH??? G???I LIVE LLM N???U C?? M???NG HO???C API KEY
      try {
        const rawAiText = await LLMClient.generateNarration(targetItem);
        if (rawAiText && rawAiText.trim().length > 30) {
          purifiedText = ContentPurifier.purify(rawAiText);
          isLiveAI = true;
        }
      } catch (err) {
        console.warn(`[AI Engine] Live LLM kh??ng ph???n h???i. T??? ?????ng k??ch ho???t B??? Sinh S?? Ph???m C???c B??? CIKM...`);
      }

      // N???U LIVE LLM KH??NG PH???N H???I -> T??? ?????NG SINH S?? PH???M CHI TI???T 65-75 T??? CHO T???NG NH??NH L??
      if (!purifiedText) {
        const segNarrations = [];
        (targetItem.sections || []).forEach(sec => {
          (sec.items || []).forEach(it => {
            const richNarr = synthesizeRichSegmentNarration(it, targetItem.title, targetItem.depth, activeProject.wpm || 140);
            it.narration = richNarr;
            segNarrations.push(`[${it.code}] ${richNarr}`);
          });
        });
        purifiedText = segNarrations.join('\n\n');
      } else {
        // C???p nh???t l???i tho???i chi ti???t v??o t???ng m???c con (item) n???u c?? format [code]
        const segPattern = /\[([a-z]\d{1,2})\]\s*([^\[]+)/gi;
        const parsedSegs = {};
        let match;
        while ((match = segPattern.exec(purifiedText)) !== null) {
          parsedSegs[match[1].trim()] = match[2].trim();
        }

        (targetItem.sections || []).forEach(sec => {
          (sec.items || []).forEach(it => {
            if (parsedSegs[it.code]) {
              it.narration = parsedSegs[it.code];
            } else if (!it.narration || it.narration.length < 35) {
              it.narration = synthesizeRichSegmentNarration(it, targetItem.title, targetItem.depth, activeProject.wpm || 140);
            }
          });
        });
      }

      setNodeParam(chKey, 'narration', purifiedText);
      if (targetSceneMatch) {
        targetSceneMatch.narration = purifiedText;
      }

      return { isLiveAI, purifiedText };
    }

    async function generateAllScenesWithAI() {
      const allSources = activeProject.sources || [
        { name: activeProject.title + '.pdf', pages: 35, size: '1.2 MB', active: true }
      ];
      const activeSources = allSources.filter(s => s.active !== false);

      const chKeys = [];
      activeSources.forEach((src, srcIdx) => {
        const originalIdx = allSources.indexOf(src);
        const rootKey = getSourceKey(src, originalIdx >= 0 ? originalIdx : srcIdx);
        if (isNodeExcluded(rootKey)) return;
        const sourceScenes = (src.scenes && src.scenes.length > 0)
          ? src.scenes
          : (originalIdx === 0 ? currentScenes : []);
        const hierarchyChapters = getProjectHierarchy(activeProject, sourceScenes, src, originalIdx >= 0 ? originalIdx : srcIdx);
        hierarchyChapters.forEach((chData, chIdx) => {
          const chKey = `ch-${rootKey}-${chIdx}`;
          if (!isNodeExcluded(chKey, [rootKey])) {
            chKeys.push({ chKey, title: getNodeParam(chKey, 'title', chData.title) });
          }
        });
      });

      if (chKeys.length === 0) {
        showToast('Kh??ng c?? ph??n c???nh n??o ??ang ho???t ?????ng ????? sinh l???i tho???i!');
        return;
      }

      const ok = await showCustomConfirm({
        title: "Vi???t To??n B??? K???ch B???n B??i Gi???ng",
        subtitle: "Chu???n s?? ph???m MOOC CIKM ??? T??? ?????ng l???p ?????y ng??n s??ch th???i l?????ng",
        message: `H??? th???ng s??? vi???t k???ch b???n s?? ph???m chuy??n s??u cho to??n b??? ${chKeys.length} ph??n c???nh (bao g???m t???t c??? c??c ph??n ??o???n con tr??n s?? ????? t?? duy).\n\n??? Ph??n b??? chi ti???t 65-75 t??? cho t???ng ph??n ??o???n 30s\n??? X??a b??? ho??n to??n kho???ng l???ng d?? th???a\n??? T??? ?????ng t???i ??u ng??? ??i???u v?? ??i???m ng???t nh???p [P1/P2/P3]`,
        icon: "???",
        confirmText: "B???t ?????u Vi???t",
        cancelText: "H???y B???"
      });
      if (!ok) return;

      showLoading(`??ang Kh???i T???o Vi???t To??n B???...`, `T???ng c???ng ${chKeys.length} ph??n c???nh...`);

      let liveCount = 0;
      let localCount = 0;

      for (let i = 0; i < chKeys.length; i++) {
        const item = chKeys[i];
        updateLoading(`??ang Vi???t L???i Tho???i (${i + 1}/${chKeys.length})...`, `Ch????ng: ${item.title}`);
        try {
          const res = await generateSceneWithAIInternal(item.chKey);
          if (res && res.isLiveAI) liveCount++;
          else localCount++;
        } catch (err) {
          console.error(`L???i sinh c???nh ${item.chKey}:`, err);
        }
      }

      hideLoading();
      renderScriptDocument();
      renderTimeline();
      if (liveCount > 0) {
        const mName = LLMClient.getConfig().model || 'Live AI';
        showToast(`???? ???? ho??n t???t vi???t k???ch b???n cho ${chKeys.length} ph??n c???nh (${liveCount} qua Live AI [${mName}], ${localCount} qua CIKM Engine)!`);
      } else {
        showToast(`???? ???? ho??n t???t vi???t k???ch b???n chi ti???t cho to??n b??? ${chKeys.length} ph??n c???nh!`);
      }
    }

    function renderScriptDocument() {
      const paper = document.getElementById('script-paper-view');
      if (!paper) return;
      paper.innerHTML = '';

      const allSources = activeProject.sources || [
        { name: activeProject.title + '.pdf', pages: 35, size: '1.2 MB', active: true }
      ];
      // L???c c??c slide/ngu???n t??i li???u ??ang ???????c t??ch ch???n (active !== false)
      const activeSources = allSources.filter(s => s.active !== false);

      if (activeSources.length === 0) {
        paper.innerHTML = `
          <div style="text-align: center; padding: 60px 20px; color: var(--text-dim); background: rgba(15, 23, 42, 0.5); border-radius: var(--radius-md); border: 1px dashed rgba(244, 63, 94, 0.4);">
            <div style="font-size: 40px; margin-bottom: 12px;">??????</div>
            <div style="font-size: 15px; font-weight: 700; color: #f87171; margin-bottom: 6px;">Kh??ng c?? slide n??o ???????c ch???n trong k???ch b???n!</div>
            <div style="font-size: 12px; color: var(--text-muted);">H??y t??ch ch???n ??t nh???t 1 slide ??? danh s??ch t??i li???u b??n tr??i ????? t??? ?????ng t???o k???ch b???n b??i gi???ng.</div>
          </div>
        `;
        const metaEl = document.getElementById('doc-summary-meta');
        if (metaEl) {
          metaEl.innerHTML = `
            <div class="meta-stat-row">?????? T???ng th???i l?????ng: <strong>0s</strong></div>
            <div class="meta-stat-row">???? 0 ch????ng t??? 0 slide</div>
          `;
        }
        updateBtnGenCountBadge(0, 0);
        return;
      }

      // Qu??t t???t c??? c??c ch????ng t??? c??c slide ??ang active
      let globalChapIdx = 0;
      const scriptItems = [];

      activeSources.forEach((src, srcIdx) => {
        const originalIdx = allSources.indexOf(src);
        const rootKey = getSourceKey(src, originalIdx >= 0 ? originalIdx : srcIdx);
        if (isNodeExcluded(rootKey)) return;

        const sourceScenes = (src.scenes && src.scenes.length > 0)
          ? src.scenes
          : (originalIdx === 0 ? currentScenes : []);
        const hierarchyChapters = getProjectHierarchy(activeProject, sourceScenes, src, originalIdx >= 0 ? originalIdx : srcIdx);

        hierarchyChapters.forEach((chData, chIdx) => {
          const chKey = `ch-${rootKey}-${chIdx}`;
          // Ki???m tra lo???i tr???
          const isEx = isNodeExcluded(chKey, [rootKey]);
          if (isEx) return;

          const customTitle = getNodeParam(chKey, 'title', chData.title);
          const customDur = getNodeParam(chKey, 'duration', chData.duration_s || 60);
          const customWpm = getNodeParam(chKey, 'wpm', 140);
          const customVisual = getNodeParam(chKey, 'visualType', chData.visual_type || 'split_screen');
          const customNotes = getNodeParam(chKey, 'notes', '');

          // L???c c??c sections & items con
          const validSections = [];
          (chData.sections || []).forEach((sec, secIdx) => {
            const secKey = `sec-${rootKey}-${chIdx}-${secIdx}`;
            if (isNodeExcluded(secKey, [chKey, rootKey])) return;

            const validItems = [];
            (sec.items || []).forEach((it, itIdx) => {
              const itKey = `item-${rootKey}-${chIdx}-${secIdx}-${itIdx}`;
              if (!isNodeExcluded(itKey, [secKey, chKey, rootKey])) {
                validItems.push(it);
              }
            });

            validSections.push({
              code: sec.code,
              title: sec.title,
              items: validItems
            });
          });

          // L???y l???i gi???ng ph?? h???p v?? l??m s???ch b???ng ContentPurifier
          const sceneMatch = sourceScenes[chIdx] || {};
          let narrationText = getNodeParam(chKey, 'narration', sceneMatch.narration || '');
          narrationText = ContentPurifier.purify(narrationText);

          globalChapIdx++;

          scriptItems.push({
            src,
            srcIdx,
            srcOrder: srcIdx + 1,
            globalChapIdx,
            chKey,
            title: customTitle,
            chapterTag: `CH????NG ${globalChapIdx}`,
            depth: chData.depth || 'core',
            duration: customDur,
            visualType: customVisual,
            visualDesc: sceneMatch.visual_purpose || customTitle,
            narration: narrationText,
            sections: validSections,
            notes: customNotes
          });
        });
      });

      if (scriptItems.length === 0) {
        paper.innerHTML = `
          <div style="text-align: center; padding: 60px 20px; color: var(--text-dim); background: rgba(15, 23, 42, 0.5); border-radius: var(--radius-md); border: 1px dashed rgba(244, 63, 94, 0.4);">
            <div style="font-size: 40px; margin-bottom: 12px;">??????</div>
            <div style="font-size: 15px; font-weight: 700; color: #f87171; margin-bottom: 6px;">To??n b??? c??c ch????ng ???? b??? lo???i b??? kh???i k???ch b???n!</div>
            <div style="font-size: 12px; color: var(--text-muted);">H??y b???m l???i n??t ??? tr??n s?? ????? ????? kh??i ph???c c??c ch????ng c???n thi???t cho b??i gi???ng c???a b???n.</div>
          </div>
        `;
        return;
      }

      // 3. TH???C HI???N ACTIVE AUTO-RESCALING V???I PROSODY PLANNER
      const rescaled = ActiveRescaler.rescale(scriptItems, activeProject.duration_s, activeProject.wpm || 140);
      const totalWords = rescaled.items.reduce((acc, it) => acc + (it.planRes ? it.planRes.words : 0), 0);

      // C???p nh???t th???ng k?? ti??u ?????
      const totalM = Math.floor(rescaled.meta.finalDuration / 60);
      const totalS = rescaled.meta.finalDuration % 60;
      const metaEl = document.getElementById('doc-summary-meta');
      const titleEl = document.getElementById('doc-active-title');

      if (titleEl) titleEl.textContent = activeProject.title;
      if (metaEl) {
        const hasScript = rescaled.meta.totalSpeech >= (rescaled.meta.targetDuration * 0.4);
        metaEl.innerHTML = `
          <div class="meta-stat-row">?????? M???c ti??u: <strong>${totalM}p ${totalS < 10 ? '0' : ''}${totalS}s</strong> (${rescaled.meta.targetDuration}s)</div>
          <div class="meta-stat-row">??????? ???? c??: <strong>${Math.round(rescaled.meta.totalSpeech)}s</strong></div>
          <div class="meta-stat-row">?????? Kho???ng ngh???: <strong>${Math.round(rescaled.meta.totalPause)}s</strong></div>
          <div class="meta-stat-row">???? <strong>${rescaled.items.length}</strong> ph??n c???nh</div>
          <div class="meta-stat-row">???? ~<strong>${totalWords}</strong> t??? ${hasScript ? '' : '<span style="color: #f59e0b; font-weight: 700;">(Ch??a sinh ?????)</span>'}</div>
        `;
      }
      updateBtnGenCountBadge(rescaled.items.length, activeSources.length);

      // Render t???ng ch????ng v??o paper
      let currentRenderSrc = null;
      rescaled.items.forEach(item => {
        if (activeSources.length > 1 && item.src !== currentRenderSrc) {
          currentRenderSrc = item.src;
          const srcDivider = document.createElement('div');
          srcDivider.className = 'script-source-divider';
          srcDivider.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin: 28px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid rgba(56, 189, 248, 0.35);">
              <span class="source-order-badge" style="background: rgba(56, 189, 248, 0.2); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.4); font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace;">
                TH??? T??? #${item.srcOrder}
              </span>
              <span style="font-size: 15px; font-weight: 800; color: #fff;">???? ${item.src.name}</span>
              <span style="font-size: 12px; color: var(--text-muted);">(${item.src.pages || 10} trang)</span>
            </div>
          `;
          paper.appendChild(srcDivider);
        }

        const startStr = formatTime(item.startS);
        const endStr = formatTime(item.endS);

        const subSecHtml = item.sections.map(sec => {
          const itemsList = sec.items.map(it => `
            <div class="script-subsec-item">??? <strong style="color: var(--cyan);">${it.code}:</strong> ${it.text}</div>
          `).join('');
          return `
            <div style="margin-top: 8px;">
              <div style="font-size: 12px; font-weight: 700; color: var(--text-main); margin-bottom: 3px;">
                <span class="script-subsec-code">${sec.code}:</span> ${sec.title}
              </div>
              <div style="padding-left: 12px; display: flex; flex-direction: column; gap: 3px;">${itemsList}</div>
            </div>
          `;
        }).join('');

        // X??Y D???NG C??C PH??N ??O???N K???CH B???N CHI TI???T T????NG ???NG T???NG NH??NH CON TR??N S?? ?????
        let hasSegments = false;
        let segmentsHtml = '';
        const chapterSegmentsList = [];

        (item.sections || []).forEach(sec => {
          (sec.items || []).forEach(it => {
            hasSegments = true;
            const itDur = it.duration || 30;
            const itTargetWords = Math.round((itDur * (activeProject.wpm || 140)) / 60);
            const itNarr = getSegmentNarration(it, item.title);
            it.narration = itNarr;
            chapterSegmentsList.push(itNarr);

            const itPlan = ProsodyPlanner.plan(itNarr, activeProject.wpm || 140);

            let itContentHtml = '';
            if (currentScriptViewMode === 'ssml') {
              itContentHtml = `<pre style="background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(56, 189, 248, 0.3); padding: 10px; border-radius: 4px; font-size: 11px; color: #a5f3fc; overflow-x: auto; font-family: 'JetBrains Mono', monospace; line-height: 1.5; white-space: pre-wrap; margin: 0;">${escapeHtml(itPlan.ssml)}</pre>`;
            } else if (currentScriptViewMode === 'plain') {
              itContentHtml = `<div style="font-size: 13px; line-height: 1.75; color: #e2e8f0;">${escapeHtml(itPlan.plain)}</div>`;
            } else {
              itContentHtml = `<div class="script-segment-body">${itPlan.html}</div>`;
            }

            const isPending = !itNarr || itNarr.trim().length === 0;

            if (isPending) {
              segmentsHtml += `
                <div class="script-segment-card pending" id="seg-card-${item.chKey}-${it.code}" style="border: 1px dashed rgba(99, 102, 241, 0.35); background: rgba(15, 23, 42, 0.45); border-radius: 8px; margin-bottom: 10px; padding: 12px 14px;">
                  <div class="script-segment-header" style="margin-bottom: 6px;">
                    <div class="script-segment-title-wrap">
                      <span class="segment-code-badge" style="background: rgba(99, 102, 241, 0.2); color: #c7d2fe;">${it.code}</span>
                      <span class="segment-title" style="font-weight: 700; color: #fff;">${it.text}</span>
                      <span class="segment-sec-tag">??? ${sec.title}</span>
                    </div>
                    <div class="script-segment-badges">
                      <span class="segment-dur-badge">?????? ${itDur}s</span>
                      <span class="segment-word-badge" style="background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2);">??? Ch??a sinh l???i tho???i</span>
                    </div>
                  </div>
                  <div style="font-size: 12px; color: var(--text-muted); display: flex; align-items: center; justify-content: space-between; padding-top: 4px;">
                    <span><em>Ch??a c?? k???ch b???n cho ph??n ??o???n n??y (~${itTargetWords} t???).</em></span>
                    <span style="font-size: 11px; color: var(--cyan); font-weight: 600;">B???m "??? AI Vi???t L???i Tho???i" ??? tr??n ????? t???o ???</span>
                  </div>
                </div>
              `;
            } else {
              segmentsHtml += `
                <div class="script-segment-card" id="seg-card-${item.chKey}-${it.code}">
                  <div class="script-segment-header">
                    <div class="script-segment-title-wrap">
                      <span class="segment-code-badge">${it.code}</span>
                      <span class="segment-title">${it.text}</span>
                      <span class="segment-sec-tag">??? ${sec.title}</span>
                    </div>
                    <div class="script-segment-badges">
                      <span class="segment-dur-badge">?????? ${itDur}s</span>
                      <span class="segment-word-badge">???? ${itPlan.words} / ~${itTargetWords} t???</span>
                    </div>
                  </div>
                  ${itContentHtml}
                </div>
              `;
            }
          });
        });

        // N???u ch????ng c?? ph??n ??o???n con, t???ng h???p l???i l???i tho???i ?????y ????? cho to??n ch????ng
        if (hasSegments && chapterSegmentsList.length > 0) {
          item.narration = chapterSegmentsList.join(' ');
          item.planRes = ProsodyPlanner.plan(item.narration, activeProject.wpm || 140);
        }

        // T??y theo currentScriptViewMode ????? render l???i tho???i ph???ng (n???u kh??ng c?? ph??n ??o???n con)
        let fallbackNarrationHtml = '';
        if (currentScriptViewMode === 'ssml') {
          fallbackNarrationHtml = `
            <pre style="background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(56, 189, 248, 0.3); padding: 14px; border-radius: 6px; font-size: 11.5px; color: #a5f3fc; overflow-x: auto; font-family: 'JetBrains Mono', monospace; line-height: 1.6; white-space: pre-wrap; margin: 0;">${escapeHtml(item.planRes ? item.planRes.ssml : item.narration)}</pre>
          `;
        } else if (currentScriptViewMode === 'plain') {
          fallbackNarrationHtml = item.planRes ? item.planRes.plain : item.narration;
        } else {
          fallbackNarrationHtml = item.planRes ? item.planRes.html : item.narration;
        }

        const sectionEl = document.createElement('div');
        sectionEl.className = 'script-chapter-section';
        sectionEl.innerHTML = `
          <div class="script-chapter-header">
            <div class="script-chapter-title-group">
              <span class="depth-tag depth-${item.depth}">${item.chapterTag}</span>
              <span class="script-chapter-name">${item.title}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <button class="script-action-btn btn-scene-ai-write" data-chkey="${item.chKey}" style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); color: #c7d2fe; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; transition: all 0.2s;" title="D??ng AI vi???t l???i tho???i s?? ph???m t???i ??u theo t???ng ph??n ??o???n">
                <span>???</span> AI Vi???t L???i Tho???i
              </button>
              <div class="script-chapter-timing">[${startStr} - ${endStr}] (${item.duration}s)</div>
            </div>
          </div>

          <div class="script-visual-directive">
            <span>???????</span> <strong>[${item.visualType}]</strong>
            <span>Ch??? d???n th??? gi??c: ${item.visualDesc}</span>
          </div>

          ${hasSegments ? `
            <div class="script-segments-list">
              ${segmentsHtml}
            </div>
          ` : `
            <div class="script-narration-body">${fallbackNarrationHtml}</div>
          `}

          ${item.notes ? `
            <div style="margin-top: 8px; padding: 6px 10px; background: rgba(56, 189, 248, 0.08); border-left: 3px solid var(--cyan); border-radius: 4px; font-size: 11.5px; color: #bae6fd;">
              ???? <strong>Ghi ch?? s?? ph???m:</strong> ${item.notes}
            </div>
          ` : ''}
        `;

        const aiBtn = sectionEl.querySelector('.btn-scene-ai-write');
        if (aiBtn) {
          aiBtn.addEventListener('click', () => {
            generateSceneWithAI(item.chKey);
          });
        }

        paper.appendChild(sectionEl);
      });
    }

    // =========================================================================
    // C??? M??Y ??I???U KHI???N GIAO DI???N & AI COPILOT PLAYBOOK (AGENTIC ENGINE)
    // T??ch bi???t ho??n to??n: LLM l??m B??? N??o L???p K??? Ho???ch (Planner, ~25 tokens)
    //                     C??? m??y JS l??m B??? Tay Ch??n Th???c Thi T???t ?????nh (Deterministic Engine)
    // =========================================================================

    // B???NG QUY CHU???N CH??? D???N H??NH ?????NG (COPILOT ACTION SCHEMA)
    const COPILOT_ACTION_SCHEMA = {
      "focus_chapter": {
        "desc": "Lia camera m?????t m?? v??o gi???a ch????ng tr??n s?? ????? v?? l??m ph??t s??ng vi???n th???",
        "params": { "chapter": "S??? th??? t??? ch????ng (v?? d??? 1, 2, 3...)" }
      },
      "open_editor": {
        "desc": "M??? ng??n k??o terminal ??? g??c d?????i ????? ch???nh s???a th??ng s???/ghi ch?? c???a ch????ng",
        "params": { "chapter": "S??? th??? t??? ch????ng" }
      },
      "close_editor": {
        "desc": "????ng ng??n k??o terminal ch???nh s???a",
        "params": {}
      },
      "switch_tab": {
        "desc": "Chuy???n ?????i tab hi???n th??? ??? c???t gi???a",
        "params": { "tab": "'mindmap' | 'script' | 'video'" }
      },
      "center_view": {
        "desc": "C??n gi???a to??n b??? s?? ????? t?? duy v??? tr???ng th??i ban ?????u",
        "params": {}
      },
      "set_only_chapters": {
        "desc": "Ch??? gi??? l???i c??c ch????ng ???????c ch??? ?????nh, ???n/lo???i b??? t???t c??? c??c ch????ng c??n l???i",
        "params": { "chapters": "M???ng c??c s??? ch????ng, v?? d??? [3, 5]" }
      },
      "exclude_chapters": {
        "desc": "???n/lo???i b??? c??c ch????ng ch??? ?????nh kh???i k???ch b???n",
        "params": { "chapters": "M???ng c??c s??? ch????ng, v?? d??? [1, 2, 4]" }
      },
      "include_chapters": {
        "desc": "B???t l???i/kh??i ph???c c??c ch????ng ???? b??? ???n v??o k???ch b???n",
        "params": { "chapters": "M???ng c??c s??? ch????ng, v?? d??? [2]" }
      },
      "set_chapter_duration": {
        "desc": "Thi???t l???p th???i l?????ng ri??ng cho m???t ch????ng v?? ph??n b??? xu???ng c??c nh??nh con",
        "params": { "chapter": "S??? th??? t??? ch????ng", "seconds": "S??? gi??y, v?? d??? 1200" }
      },
      "set_total_minutes": {
        "desc": "Thi???t l???p th???i gian t???ng to??n b??i gi???ng (chia theo t??? l???)",
        "params": { "minutes": "S??? ph??t t???ng, v?? d??? 40" }
      },
      "lock_chapter": {
        "desc": "Kh??a ho???c m??? kh??a th???i l?????ng c???a ch????ng",
        "params": { "chapter": "S??? th??? t??? ch????ng", "locked": "true | false" }
      },
      "set_speed": {
        "desc": "??i???u ch???nh t???c ????? nh???p ?????c WPM to??n b??i",
        "params": { "wpm": "120 | 140 | 165 | 190 ho???c rate: '0.85' | '1.0' | '1.2' | '1.35'" }
      },
      "set_voice": {
        "desc": "?????i gi???ng ?????c AI (TTS Voice)",
        "params": { "voice": "'quynh_anh' | 'nam_an' | 'mai_phuong' | 'minh_quang' | 'jenny_en' | 'guy_en'" }
      }
    };

    function getAllChaptersInfo() {
      const chapters = [];
      Object.values(currentNodesMap).forEach(n => {
        if (n.level === 1) {
          const parts = n.key.split('-');
          const idx = parseInt(parts[parts.length - 1]);
          const num = !isNaN(idx) ? (idx + 1) : (chapters.length + 1);
          chapters.push({
            key: n.key,
            num: num,
            title: n.data?.title || `Ch????ng ${num}`,
            duration: n.data?.duration || 60,
            isExcluded: isNodeExcluded(n.key),
            isLocked: getNodeParam(n.key, 'isLocked', false)
          });
        }
      });
      chapters.sort((a, b) => a.num - b.num);
      return chapters;
    }
