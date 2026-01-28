import {
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  Typography,
} from "@mui/material";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import LogoutIcon from "@mui/icons-material/Logout";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";
import { tokenStore, userStore } from "../services/api";
import { useMemo, useState } from "react";
import { GridSearchIcon } from "@mui/x-data-grid";

type NavLink = {
  label: string;
  link: string;
  variant?: "contained" | "outlined";
  adminOnly?: boolean;
  icon?: React.ReactNode;
};

type NavbarProps = {
  title: string;
  subtitle?: string;
  links: NavLink[];
};

export default function Navbar({ title, subtitle, links }: NavbarProps) {
  const navigate = useNavigate();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const user = userStore.get();

  const facilityLabel = useMemo(() => {
    if (!user) return "Healthcare Provider";
    if (user.facility_name) {
      const suffix = user.facility_type === "hospital" ? "Hos" : "PHC";
      return `${user.facility_name} (${suffix})`;
    }
    return "Healthcare Provider";
  }, [user]);

  const filteredLinks = useMemo(() => {
    return links.filter((l) => {
      if (!l.adminOnly) return true;
      return user?.role === "admin";
    });
  }, [links, user]);

  return (
    <Card
      sx={{
        borderRadius: 3,
        border: "1px solid rgba(15, 23, 42, 0.10)",
        boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: { xs: 2.5, md: 3.5 },
          py: { xs: 2.5, md: 3 },
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={{ xs: 2, md: 3 }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", md: "center" }}
        >
          <Stack spacing={0.5}>
            <Typography
              variant="h5"
              sx={{ fontWeight: 800, letterSpacing: -0.2 }}
            >
              {title}
            </Typography>
            {subtitle && (
              <Typography
                variant="body2"
                sx={{ opacity: 0.9, lineHeight: 1.7 }}
              >
                {subtitle}
              </Typography>
            )}
          </Stack>

          <Stack
            direction="row"
            spacing={1.25}
            sx={{ width: { xs: "100%", md: "auto" } }}
            justifyContent={{ xs: "space-between", md: "flex-end" }}
            alignItems="center"
          >
            {filteredLinks.map((btn) => (
              <Button
                key={btn.label}
                variant={btn.variant ?? "contained"}
                onClick={() => navigate(btn.link)}
                sx={{
                  textTransform: "none",
                  fontWeight: 700,
                  borderRadius: 2,
                  background:
                    btn.variant === "outlined"
                      ? "transparent"
                      : "rgba(255,255,255,0.95)",
                  color: btn.variant === "outlined" ? "white" : "#4C51BF",
                  "&:hover": {
                    background:
                      btn.variant === "outlined"
                        ? "rgba(255,255,255,0.10)"
                        : "white",
                  },
                  flex: { xs: 1, md: "unset" },
                  px: 2.25,
                }}
                startIcon={btn.icon}
              >
                {btn.label}
              </Button>
            ))}

            <Box
              sx={{
                ml: { xs: 0, md: 2 },
                pl: { xs: 0, md: 2 },
                borderLeft: {
                  xs: "none",
                  md: "1px solid rgba(255,255,255,0.2)",
                },
                display: { xs: "none", sm: "block" },
              }}
            >
              <Button
                onClick={(e) => setAnchorEl(e.currentTarget)}
                endIcon={<ArrowDropDownIcon />}
                sx={{
                  textTransform: "none",
                  color: "white",
                  borderRadius: 2,
                  px: 1.5,
                  py: 0.75,
                  "&:hover": { background: "rgba(255,255,255,0.10)" },
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1}>
                  <AccountCircleIcon sx={{ fontSize: 24 }} />
                  <Stack spacing={0} alignItems="flex-start">
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        lineHeight: 1.2,
                        fontSize: 13,
                      }}
                    >
                      {user?.full_name || user?.username || "User"}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "rgba(255,255,255,0.75)",
                        lineHeight: 1,
                        fontSize: 10,
                      }}
                    >
                      {facilityLabel}
                    </Typography>
                  </Stack>
                </Stack>
              </Button>

              <Menu
                anchorEl={anchorEl}
                open={menuOpen}
                onClose={() => setAnchorEl(null)}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                transformOrigin={{ vertical: "top", horizontal: "right" }}
              >
                <MenuItem
                  onClick={() => {
                    setAnchorEl(null);
                    tokenStore.clear();
                    navigate("/login", { replace: true });
                  }}
                >
                  <LogoutIcon sx={{ mr: 1.5 }} />
                  Logout
                </MenuItem>
              </Menu>
            </Box>

            <IconButton
              onClick={() => {
                tokenStore.clear();
                navigate("/login", { replace: true });
              }}
              sx={{
                display: { xs: "flex", sm: "none" },
                color: "white",
              }}
            >
              <LogoutIcon />
            </IconButton>
          </Stack>
        </Stack>
      </Box>
    </Card>
  );
}

export const navLinks = [
  { label: "Dashboard", link: "/dashboard" },
  { label: "All Users", link: "/admin/users", adminOnly: true },
  { label: "Pending Users", link: "/admin/pending", adminOnly: true },
  { label: "Add patient", link: "/patients/new" },
  {
    label: "Patients",
    link: "/patients",
    variant: "outlined" as const,
    icon: <SearchIcon />,
  },
];
