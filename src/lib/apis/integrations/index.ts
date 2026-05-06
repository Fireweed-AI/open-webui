import { WEBUI_API_BASE_URL } from '$lib/constants';

const handleJsonResponse = async (res: Response) => {
	if (!res.ok) {
		throw await res.json();
	}

	return res.json();
};

const getErrorDetail = (err: any) => {
	return err?.detail || err?.message || 'Request failed';
};

export const getSourcesConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sources/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSourceConnections = async (token: string, provider?: string) => {
	let error = null;
	const query = provider ? `?provider=${encodeURIComponent(provider)}` : '';

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections${query}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSourceProviders = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/providers`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSourceConnectionById = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getProviderConnectUrl = async (
	token: string,
	providerId: string,
	nextPath: string
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/integrations/providers/${providerId}/connect/start`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ next_path: nextPath })
		}
	)
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSourceConnection = async (token: string, connectionId: string, body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSourceConnectionSelectionToken = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}/selection-token`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const syncSourceConnection = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const previewSourceConnection = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}/preview`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSourceConnectionFiles = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}/files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSourceConnectionFiles = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}/files`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSourceConnection = async (token: string, connectionId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/connections/${connectionId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSourcesConfig = async (token: string, body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sources/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const syncGDrive = async (token: string, body: object = {}) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getGDriveFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteGDriveFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/files`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const syncSharePoint = async (token: string, body: object = {}) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSharePointFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSharePointFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/files`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSharePointSites = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/sites`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
