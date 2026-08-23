/*
 * Shared password-strength UI used by the Register and Reset Password pages.
 *
 * The classifier mirrors the backend rules in app/frontend/main.py
 * (classify_password_strength / WeakPassword validator) exactly:
 *   strong   = at least 8 chars with upper, lower, number and special
 *   moderate = at least 8 chars with a letter plus any of upper/number/special
 *   weak     = everything else
 *
 * Strength meter initializes only when the meter markup exists.
 * Live confirm-match checking runs only on inputs marked with
 * data-live-match-check so other pages keep their existing behavior.
 */
(function () {
    'use strict';

    function classifyPasswordStrength(password) {
        if (
            password.length >= 8 &&
            /[a-z]/.test(password) &&
            /[A-Z]/.test(password) &&
            /[0-9]/.test(password) &&
            /[^A-Za-z0-9]/.test(password)
        ) {
            return 'strong';
        }
        if (
            password.length >= 8 &&
            /[A-Za-z]/.test(password) && (
                /[A-Z]/.test(password) ||
                /[0-9]/.test(password) ||
                /[^A-Za-z0-9]/.test(password)
            )
        ) {
            return 'moderate';
        }
        return 'weak';
    }

    function initStrengthMeter() {
        const passwordInput = document.getElementById('password');
        const wrapper = document.getElementById('passwordStrengthWrapper');
        const bar = document.getElementById('passwordStrengthBar');
        const label = document.getElementById('passwordStrengthLabel');

        if (!passwordInput || !wrapper || !bar || !label) return;

        function updateStrength() {
            const level = classifyPasswordStrength(passwordInput.value);

            if (level === 'strong') {
                bar.style.width = '100%';
                bar.className = 'progress-bar bg-success';
                bar.setAttribute('aria-valuenow', '100');
                label.textContent = 'Strong';
                label.className = 'form-text small text-success';
            } else if (level === 'moderate') {
                bar.style.width = '66%';
                bar.className = 'progress-bar bg-warning';
                bar.setAttribute('aria-valuenow', '66');
                label.textContent = 'Moderate';
                label.className = 'form-text small text-warning';
            } else {
                bar.style.width = '33%';
                bar.className = 'progress-bar bg-danger';
                bar.setAttribute('aria-valuenow', '33');
                label.textContent = 'Weak';
                label.className = 'form-text small text-danger';
            }
        }

        passwordInput.addEventListener('focus', () => {
            wrapper.classList.remove('d-none');
            updateStrength();
        });

        passwordInput.addEventListener('input', () => {
            if (!wrapper.classList.contains('d-none')) updateStrength();
        });
    }

    function initLiveConfirmCheck() {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        const feedback = document.getElementById('confirmMatchFeedback');

        if (!passwordInput || !confirmPasswordInput || !feedback) return;
        if (!confirmPasswordInput.hasAttribute('data-live-match-check')) return;

        function showMismatch() {
            confirmPasswordInput.classList.add('is-invalid');
            feedback.textContent = 'Passwords do not match.';
            feedback.classList.add('d-block');
        }

        function clearMismatch() {
            confirmPasswordInput.classList.remove('is-invalid');
            feedback.textContent = '';
            feedback.classList.remove('d-block');
        }

        function updateMatchState() {
            const confirmValue = confirmPasswordInput.value;

            if (!confirmValue || confirmValue === passwordInput.value) {
                clearMismatch();
                return;
            }

            showMismatch();
        }

        confirmPasswordInput.addEventListener('input', updateMatchState);
        passwordInput.addEventListener('input', updateMatchState);

        // Re-check when returning to the page (e.g. after Show/Hide toggles
        // or browser autofill) so the fields never report a stale state.
        window.addEventListener('pageshow', updateMatchState);
    }

    document.addEventListener('DOMContentLoaded', () => {
        initStrengthMeter();
        initLiveConfirmCheck();
    });

    // Exposed for testing purposes only.
    window.__classifyPasswordStrength = classifyPasswordStrength;
})();
