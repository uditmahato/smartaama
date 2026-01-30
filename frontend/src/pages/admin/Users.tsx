import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import {
  Alert,
  Box,
  Button,
  Card,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import Navbar, { navLinks } from "../../components/Navbar";

type User = {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  is_approved: boolean;
  facility_type: string | null;
};

export default function Users() {
  const [rows, setRows] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const res = await api.get("/admin/users");
    setRows(res.data);
    setLoading(false);
  }

  async function remove(id: string) {
    if (!confirm("Delete this user?")) return;
    await api.delete(`/admin/users/${id}`);
    load();
  }

  useEffect(() => {
    load();
  }, []);

  const columns: GridColDef[] = [
    { field: "username", headerName: "Username", flex: 1 },
    { field: "role", headerName: "Role", width: 140 },
    {
      field: "facility_type",
      headerName: "Facility",
      width: 120,
    },
    {
      field: "is_active",
      headerName: "Active",
      width: 120,
      valueFormatter: ({ value }) => (value ? "Yes" : "No"),
    },
    {
      field: "is_approved",
      headerName: "Approved",
      width: 120,
      valueFormatter: ({ value }) => (value ? "Yes" : "No"),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 140,
      sortable: false,
      renderCell: (params) => (
        <Button
          color="error"
          size="small"
          variant="contained"
          onClick={() => remove(params.row.id)}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#F6F7FB",
        py: { xs: 2, md: 3 },
        px: { xs: 0.5, sm: 1, md: 1.5 },
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <Navbar
        title="Users"
        subtitle="Manage users and their roles"
        links={navLinks}
      />
      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
        />
      </div>
    </Box>
  );
}
