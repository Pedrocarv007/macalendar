/**
 * Módulo para geração automática de documentos
 * Integração com o sistema MAC Calendar
 */

class DocumentGenerator {
  constructor(apiBaseUrl = '/api/documents') {
    const base = window.API_BASE_URL || '';
    // Garantir prefixo correto (ex.: /mac/api)
    this.apiUrl = apiBaseUrl.startsWith('http') ? apiBaseUrl : `${base}${apiBaseUrl}`;
  }

  /**
   * Gerar cartão de boas-vindas
   * @param {number} employeeId - ID do colaborador
   * @param {number} restaurantId - ID do restaurante
   * @returns {Promise<Object>} Documento gerado
   */
  async generateWelcomeCard(employeeId, restaurantId) {
    return this._generateDocument({
      document_type: 'bem_vindo',
      employee_id: employeeId,
      restaurant_id: restaurantId
    });
  }

  /**
   * Gerar cartão de aniversário
   * @param {number} employeeId - ID do colaborador
   * @param {number} restaurantId - ID do restaurante
   * @returns {Promise<Object>} Documento gerado
   */
  async generateBirthdayCard(employeeId, restaurantId) {
    return this._generateDocument({
      document_type: 'aniversario',
      employee_id: employeeId,
      restaurant_id: restaurantId
    });
  }

  /**
   * Enviar requisição de geração de documento
   * @private
   */
  async _generateDocument(data) {
    try {
      const response = await fetch(`${this.apiUrl}/generate-auto`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        let errorText = await response.text();
        let errorJson = null;
        try { errorJson = JSON.parse(errorText); } catch (e) { /* fallback */ }
        throw new Error((errorJson && (errorJson.error || errorJson.message)) || errorText || 'Erro ao gerar documento');
      }

      const result = await response.json().catch(() => ({}));
      if (!result || !result.document) {
        throw new Error('Resposta inválida da API');
      }
      return {
        success: true,
        document: result.document,
        filePath: result.file_path
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Fazer download do documento
   * @param {string} filePath - Caminho do arquivo
   * @param {string} fileName - Nome para salvar (opcional)
   */
  downloadDocument(filePath, fileName = null) {
    const link = document.createElement('a');
    link.href = filePath;
    link.download = fileName || filePath.split('/').pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Exibir documento em janela nova
   * @param {string} filePath - Caminho do arquivo
   */
  viewDocument(filePath) {
    window.open(filePath, '_blank');
  }
}

/**
 * Exemplo de uso integrado na interface
 */
document.addEventListener('DOMContentLoaded', function() {
  const docGen = new DocumentGenerator();

  // Exemplo 1: Botão para gerar cartão de boas-vindas
  const welcomeBtn = document.getElementById('generate-welcome-btn');
  if (welcomeBtn) {
    welcomeBtn.addEventListener('click', async () => {
      const employeeId = document.getElementById('employee-id')?.value;
      const restaurantId = document.getElementById('restaurant-id')?.value;

      if (!employeeId || !restaurantId) {
        alert('Selecione um colaborador e restaurante');
        return;
      }

      welcomeBtn.disabled = true;
      welcomeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';

      const result = await docGen.generateWelcomeCard(employeeId, restaurantId);

      welcomeBtn.disabled = false;
      welcomeBtn.innerHTML = '<i class="fas fa-gift"></i> Gerar Cartão de Boas-vindas';

      if (result.success) {
        Utils.showToast('Cartão gerado com sucesso!', 'success');
        docGen.viewDocument(result.document.file_path);
      } else {
        Utils.showAlert(result.error, 'error');
      }
    });
  }

  // Exemplo 2: Botão para gerar cartão de aniversário
  const birthdayBtn = document.getElementById('generate-birthday-btn');
  if (birthdayBtn) {
    birthdayBtn.addEventListener('click', async () => {
      const employeeId = document.getElementById('employee-id')?.value;
      const restaurantId = document.getElementById('restaurant-id')?.value;

      if (!employeeId || !restaurantId) {
        alert('Selecione um colaborador e restaurante');
        return;
      }

      birthdayBtn.disabled = true;
      birthdayBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';

      const result = await docGen.generateBirthdayCard(employeeId, restaurantId);

      birthdayBtn.disabled = false;
      birthdayBtn.innerHTML = '<i class="fas fa-birthday-cake"></i> Gerar Cartão de Aniversário';

      if (result.success) {
        Utils.showToast('Cartão gerado com sucesso!', 'success');
        docGen.downloadDocument(result.document.file_path);
      } else {
        Utils.showAlert(result.error, 'error');
      }
    });
  }

  // Exemplo 3: Modal para gerar cartão customizado
  const customBtn = document.getElementById('generate-custom-btn');
  if (customBtn) {
    customBtn.addEventListener('click', () => {
      // Mostrar modal ou prompt
      const title = prompt('Título do cartão:');
      const text = prompt('Texto adicional:');

      if (!title) return;

      customBtn.disabled = true;
      customBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';

      const employeeId = document.getElementById('employee-id')?.value;
      const restaurantId = document.getElementById('restaurant-id')?.value;

      docGen.generateCustomCard(employeeId, restaurantId, title, text).then(result => {
        customBtn.disabled = false;
        customBtn.innerHTML = '<i class="fas fa-star"></i> Gerar Cartão Personalizado';

        if (result.success) {
          Utils.showToast('Cartão customizado gerado!', 'success');
          docGen.viewDocument(result.document.file_path);
        } else {
          Utils.showAlert(result.error, 'error');
        }
      });
    });
  }
});

// Exportar para uso em outros scripts
if (typeof window !== 'undefined') {
  window.DocumentGenerator = DocumentGenerator;
}
