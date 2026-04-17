/**
 * MAC Calendar - DOM Utilities
 * Funções para manipulação do DOM
 */

class DOM {
    /**
     * Select elemento
     */
    static $(selector) {
        return document.querySelector(selector);
    }

    /**
     * Select múltiplos elementos
     */
    static $$(selector) {
        return document.querySelectorAll(selector);
    }

    /**
     * Criar elemento
     */
    static createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        for (const [key, value] of Object.entries(attributes)) {
            if (key === 'class') {
                element.className = value;
            } else if (key === 'style') {
                Object.assign(element.style, value);
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, value);
            } else {
                element[key] = value;
            }
        }

        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Element) {
                element.appendChild(child);
            }
        });

        return element;
    }

    /**
     * Adicionar clase
     */
    static addClass(element, className) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.classList.add(className);
    }

    /**
     * Remover classe
     */
    static removeClass(element, className) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.classList.remove(className);
    }

    /**
     * Toggle classe
     */
    static toggleClass(element, className) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.classList.toggle(className);
    }

    /**
     * Verificar se tem classe
     */
    static hasClass(element, className) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        return element ? element.classList.contains(className) : false;
    }

    /**
     * Setar innerHTML
     */
    static setHTML(element, html) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.innerHTML = html;
    }

    /**
     * Setar texto
     */
    static setText(element, text) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.textContent = text;
    }

    /**
     * Setar atributo
     */
    static setAttribute(element, attr, value) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.setAttribute(attr, value);
    }

    /**
     * Get atributo
     */
    static getAttribute(element, attr) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        return element ? element.getAttribute(attr) : null;
    }

    /**
     * Show elemento
     */
    static show(element) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.style.display = '';
    }

    /**
     * Hide elemento
     */
    static hide(element) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.style.display = 'none';
    }

    /**
     * Toggle visibilidade
     */
    static toggle(element) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) {
            element.style.display = element.style.display === 'none' ? '' : 'none';
        }
    }

    /**
     * Event listener
     */
    static on(element, event, handler) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.addEventListener(event, handler);
    }

    /**
     * Remove event listener
     */
    static off(element, event, handler) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.removeEventListener(event, handler);
    }

    /**
     * Delegate event
     */
    static delegate(parent, selector, event, handler) {
        if (typeof parent === 'string') {
            parent = this.$(parent);
        }
        
        if (parent) {
            parent.addEventListener(event, (e) => {
                if (e.target.matches(selector)) {
                    handler.call(e.target, e);
                }
            });
        }
    }

    /**
     * Get valor de input/select/textarea
     */
    static getValue(element) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        return element ? element.value : null;
    }

    /**
     * Set valor de input/select/textarea
     */
    static setValue(element, value) {
        if (typeof element === 'string') {
            element = this.$(element);
        }
        if (element) element.value = value;
    }

    /**
     * Get dados de formulário
     */
    static getFormData(formId) {
        const form = typeof formId === 'string' ? this.$(formId) : formId;
        if (!form) return null;
        
        const formData = new FormData(form);
        return Object.fromEntries(formData);
    }

    /**
     * Set dados no formulário
     */
    static setFormData(formId, data) {
        const form = typeof formId === 'string' ? this.$(formId) : formId;
        if (!form) return;

        for (const [key, value] of Object.entries(data)) {
            const input = form.elements[key];
            if (input) {
                input.value = value;
            }
        }
    }
}

// Fazer DOM disponível globalmente
window.DOM = DOM;
