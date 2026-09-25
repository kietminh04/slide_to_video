    function openNodeTuningTerminal(nodeOrKey, cardEl) {
      let nodeKey = typeof nodeOrKey === 'string' ? nodeOrKey : nodeOrKey.key;
      let nodeTitle = '';
      let duration = 60;
      let wpm = 140;
      let visualType = 'split_screen';
      let nodeObj = null;

      if (typeof nodeOrKey === 'object') {
        nodeObj = nodeOrKey;
        nodeTitle = nodeObj.data.title || nodeObj.data.text || nodeKey;
        duration = nodeObj.data.duration || (nodeObj.children && nodeObj.children.length > 0 ? 90 : 30);
        wpm = nodeObj.data.wpm || 140;
        visualType = nodeObj.data.visualType || 'split_screen';
      } else {
        nodeObj = currentNodesMap[nodeKey] || null;
        nodeTitle = getNodeParam(nodeKey, 'title', nodeKey);
        duration = (nodeObj && nodeObj.data && nodeObj.data.duration) ? nodeObj.data.duration : getNodeParam(nodeKey, 'duration', 30);
        wpm = getNodeParam(nodeKey, 'wpm', 140);
        visualType = getNodeParam(nodeKey, 'visualType', 'split_screen');
      }

      // Đọc các giá trị đã lưu tuỳ biến trước đó
      const customTitle = getNodeParam(nodeKey, 'title', nodeTitle);
      const customDur = (nodeObj && nodeObj.data && nodeObj.data.duration) ? nodeObj.data.duration : getNodeParam(nodeKey, 'duration', duration);
      const customWpm = getNodeParam(nodeKey, 'wpm', wpm);
      const customVis = getNodeParam(nodeKey, 'visualType', visualType);
      const customNotes = getNodeParam(nodeKey, 'notes', '');

      currentTuningTarget = {
        nodeKey,
        nodeTitle: customTitle,
        duration: customDur,
        wpm: customWpm,
        visualType: customVis,
        notes: customNotes,
        nodeObj: nodeObj
      };

      // Highlight card đang được chỉnh sửa trên sơ đồ
      document.querySelectorAll('.is-being-edited').forEach(el => el.classList.remove('is-being-edited'));
      const activeCard = cardEl || document.getElementById(`node-${nodeKey}`);
      if (activeCard) activeCard.classList.add('is-being-edited');

      const drawer = document.getElementById('mindmap-terminal-drawer');
      if (!drawer) return;

      const titleDisplay = document.getElementById('terminal-target-title');
      if (titleDisplay) {
        titleDisplay.textContent = `CẤU HÌNH: ${customTitle.length > 32 ? customTitle.substring(0, 30) + '...' : customTitle}`;
      }
      const keyDisplay = document.getElementById('terminal-target-key');
      if (keyDisplay) keyDisplay.textContent = nodeKey;

      const inputTitle = document.getElementById('terminal-node-title');
      if (inputTitle) inputTitle.value = customTitle;

      const durSlider = document.getElementById('slider-terminal-duration');
      const durVal = document.getElementById('val-terminal-duration');
      if (durSlider && durVal) {
        durSlider.min = 5;
        durSlider.max = Math.max(300, Math.ceil((customDur || 60) * 1.5));
        durSlider.step = 5;
        durSlider.value = customDur || 30;
        const m = Math.floor(durSlider.value / 60);
        const s = durSlider.value % 60;
        durVal.textContent = `${durSlider.value}s (${m > 0 ? m + 'p' : ''}${s < 10 ? '0' : ''}${s}s)`;
      }

      const wpmSlider = document.getElementById('slider-terminal-wpm');
      const wpmVal = document.getElementById('val-terminal-wpm');
      if (wpmSlider && wpmVal) {
        wpmSlider.value = customWpm || 140;
        wpmVal.textContent = `${wpmSlider.value} WPM`;
      }

      const selectVisual = document.getElementById('select-terminal-visual');
      if (selectVisual && customVis) {
        selectVisual.value = customVis;
      }

      const notesTextarea = document.getElementById('terminal-node-notes');
      if (notesTextarea) {
        notesTextarea.value = customNotes || '';
      }

      const statusEl = document.getElementById('terminal-status');
      if (statusEl) {
        statusEl.textContent = `Đang hiệu chỉnh: ${nodeKey} (${customTitle})`;
        statusEl.style.color = 'var(--cyan)';
      }

      // Đảm bảo tab Sơ Đồ đang được kích hoạt khi mở terminal tinh chỉnh
      if (typeof switchCenterTab === 'function') {
        const mindmapTab = document.getElementById('tab-content-mindmap');
        if (!mindmapTab || !mindmapTab.classList.contains('active')) {
          switchCenterTab('mindmap');
        }
      }

      // Trượt thanh terminal lên từ đáy ô giữa (chuẩn Image 2, chiều cao thoáng 380px)
      drawer.classList.add('is-open');

      // Tự động căn chỉnh node lên phần nhìn thấy phía trên terminal nếu đang bị che khuất
      if (nodeObj && typeof panY !== 'undefined' && typeof zoomScale !== 'undefined') {
        const pane = document.getElementById('tab-content-mindmap');
        if (pane) {
          const paneRect = pane.getBoundingClientRect();
          const nodeScreenY = panY + (nodeObj.y + (nodeObj.height || 60)) * zoomScale;
          const drawerTopScreenY = paneRect.height - 390;
          if (nodeScreenY > drawerTopScreenY) {
            const diff = nodeScreenY - drawerTopScreenY + 50;
            panY -= diff;
            if (typeof applyTransform === 'function') applyTransform();
          }
        }
      }
    }