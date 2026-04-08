document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const taskSelect = document.getElementById('task-select');
    const initialState = document.getElementById('initial-state');
    const statsSection = document.getElementById('stats-section');
    const documentContainer = document.getElementById('document-container');
    const resultsPanel = document.getElementById('results-panel');
    const actionBtns = document.querySelectorAll('.action-btn');
    const restartBtn = document.getElementById('restart-btn');

    const updateDOM = (state) => {
        document.getElementById('step-count').innerText = state.clauses_reviewed;
        document.getElementById('total-count').innerText = state.total_clauses;
        document.getElementById('reward-value').innerText = (+state.cumulative_reward).toFixed(2);
        document.getElementById('flags-value').innerText = state.flags_raised.length;

        if (state.done) {
            documentContainer.style.display = 'none';
            resultsPanel.style.display = 'block';
            document.getElementById('final-score').innerText = (+state.cumulative_reward).toFixed(2);
            actionBtns.forEach(btn => btn.disabled = true);
        } else if (state.current_clause) {
            document.getElementById('clause-id').innerText = state.current_clause.id;
            document.getElementById('clause-category').innerText = state.current_clause.category;
            document.getElementById('clause-text').innerText = state.current_clause.text;
        }
    };

    const resetTask = async () => {
        const taskId = taskSelect.value;
        try {
            startBtn.disabled = true;
            startBtn.innerText = 'Loading...';
            
            const res = await fetch('/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: taskId })
            });
            const state = await res.json();
            
            initialState.style.display = 'none';
            statsSection.style.display = 'flex';
            documentContainer.style.display = 'block';
            resultsPanel.style.display = 'none';
            
            actionBtns.forEach(btn => btn.disabled = false);
            updateDOM(state);
            
        } catch (e) {
            console.error('Failed to reset', e);
            alert('Failed to reset environment. Check console.');
        } finally {
            startBtn.disabled = false;
            startBtn.innerText = 'Begin Evaluation';
        }
    };

    const submitAction = async (action) => {
        try {
            actionBtns.forEach(btn => btn.disabled = true); // prevent double clicks
            const res = await fetch('/step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            const data = await res.json();
            updateDOM(data.state);
        } catch (e) {
            console.error('Failed to submit action', e);
            alert('Failed to submit action. Check console.');
        } finally {
            // Only re-enable if we are not done
            if(documentContainer.style.display !== 'none') {
                actionBtns.forEach(btn => btn.disabled = false);
            }
        }
    };

    startBtn.addEventListener('click', resetTask);
    
    restartBtn.addEventListener('click', () => {
        resultsPanel.style.display = 'none';
        initialState.style.display = 'flex';
        statsSection.style.display = 'none';
        actionBtns.forEach(btn => btn.disabled = true);
        // We do not reset the select box natively, just visual return to top
    });

    actionBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            submitAction(action);
        });
    });
});
