'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  TextField,
  IconButton,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemButton
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import SearchIcon from '@mui/icons-material/Search'
import {
  predictSocApi,
  adjacentSocsApi,
  getSocDetailsApi
} from '../utils/socAPI'
import type { SocPrediction, AdjacentSocEntry } from '../utils/socAPI'

interface SocCodeModalProps {
  open: boolean
  onClose: () => void
  skills: string[]
  socCode: string | null
  onSocCodeChange: (code: string | null) => void
}

export default function SocCodeModal({
  open,
  onClose,
  skills,
  socCode,
  onSocCodeChange
}: SocCodeModalProps) {
  const [predictions, setPredictions] = useState<SocPrediction[]>([])
  const [adjacentSocs, setAdjacentSocs] = useState<AdjacentSocEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showChangeInput, setShowChangeInput] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [currentTitle, setCurrentTitle] = useState<string | null>(null)
  const [currentScore, setCurrentScore] = useState<number | null>(null)

  // Reset internal state and load data when modal opens or socCode/skills change
  useEffect(() => {
    if (!open) return

    setShowChangeInput(false)
    setSearchQuery('')
    setError(null)
    setPredictions([])

    loadInitialData()
  }, [open])

  const loadInitialData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      if (socCode) {
        // User has a locked SOC — fetch adjacent SOCs + details
        const [adjResult, detailResult] = await Promise.all([
          adjacentSocsApi(socCode, 5, skills.length > 0 ? skills : undefined),
          getSocDetailsApi(socCode)
        ])

        setAdjacentSocs(adjResult.same_category)
        setCurrentTitle(detailResult?.title ?? null)
        setCurrentScore(null)
      } else if (skills.length > 0) {
        // Auto-detect mode — predict SOC from skills
        const predResult = await predictSocApi(skills, 5, 0.6)
        setPredictions(predResult.predictions)

        if (predResult.predictions.length > 0) {
          const top = predResult.predictions[0]
          setCurrentTitle(top.title)
          setCurrentScore(top.score)

          // Also fetch adjacent SOCs for top prediction
          const adjResult = await adjacentSocsApi(top.soc, 5, skills)
          setAdjacentSocs(adjResult.same_category)
        } else {
          setCurrentTitle(null)
          setCurrentScore(null)
          setAdjacentSocs([])
        }
      } else {
        // No skills, no selection
        setCurrentTitle(null)
        setCurrentScore(null)
        setAdjacentSocs([])
      }
    } catch (err) {
      console.warn('[SocCodeModal] Failed to load SOC data:', err)
      setError('Failed to load SOC data. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [socCode, skills])

  const handleSelectSoc = useCallback(
    async (code: string, title: string, score?: number) => {
      // Commit the selection to parent immediately
      setCurrentTitle(title)
      setCurrentScore(score ?? null)
      setShowChangeInput(false)
      onSocCodeChange(code)

      // Fetch adjacent SOCs for newly selected code
      setLoading(true)
      try {
        const adjResult = await adjacentSocsApi(
          code,
          5,
          skills.length > 0 ? skills : undefined
        )
        setAdjacentSocs(adjResult.same_category)
      } catch (err) {
        console.warn('[SocCodeModal] Failed to fetch adjacent SOCs:', err)
      } finally {
        setLoading(false)
      }
    },
    [skills, onSocCodeChange]
  )

  const handleReset = useCallback(() => {
    onSocCodeChange(null)
    setShowChangeInput(false)
  }, [onSocCodeChange])

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return
    setLoading(true)
    try {
      const result = await predictSocApi([searchQuery], 5, 0.6)
      setPredictions(result.predictions)
    } catch (err) {
      console.warn('[SocCodeModal] Search failed:', err)
    } finally {
      setLoading(false)
    }
  }, [searchQuery])

  const isCurrentPrediction = (pred: SocPrediction) =>
    socCode !== null && pred.soc === socCode

  return (
    <Dialog open={open} onClose={onClose} maxWidth='sm' fullWidth>
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pb: 1
        }}
      >
        <Typography variant='h6' fontWeight={600}>
          Job Classification (SOC Code)
        </Typography>
        <IconButton onClick={onClose} size='small'>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Typography color='error' sx={{ mb: 2 }}>
            {error}
          </Typography>
        )}

        {!loading && !error && (
          <>
            {/* Current SOC Display */}
            <Box sx={{ mb: 3 }}>
              <Typography variant='subtitle2' color='text.secondary' gutterBottom>
                {socCode
                  ? 'Selected Classification'
                  : 'Detected Classification'}
              </Typography>
              {socCode || predictions.length > 0 ? (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    flexWrap: 'wrap'
                  }}
                >
                  <Chip
                    label={`${socCode || predictions[0]?.soc || ''}${currentTitle ? ` \u2014 ${currentTitle}` : ''}`}
                    color={socCode ? 'primary' : 'default'}
                    variant={socCode ? 'filled' : 'outlined'}
                    sx={{ fontWeight: 600, fontSize: '0.9rem', py: 2.5, px: 1 }}
                  />
                  {currentScore !== null && (
                    <Typography variant='body2' color='text.secondary'>
                      Confidence: {Math.round(currentScore)}%
                    </Typography>
                  )}
                </Box>
              ) : (
                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{ fontStyle: 'italic' }}
                >
                  No skills detected yet. Add skills to auto-detect a
                  classification.
                </Typography>
              )}
            </Box>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
              <Button
                size='small'
                variant='outlined'
                startIcon={<SearchIcon />}
                onClick={() => setShowChangeInput(!showChangeInput)}
              >
                {showChangeInput ? 'Hide Search' : 'Change SOC'}
              </Button>
              {socCode && (
                <Button
                  size='small'
                  variant='text'
                  color='warning'
                  startIcon={<RestartAltIcon />}
                  onClick={handleReset}
                >
                  Reset to Auto-Detect
                </Button>
              )}
            </Box>

            {/* Change SOC Input */}
            {showChangeInput && (
              <Box sx={{ mb: 3, display: 'flex', gap: 1 }}>
                <TextField
                  size='small'
                  fullWidth
                  placeholder='Search by SOC code or job title...'
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSearch()
                  }}
                />
                <Button variant='contained' size='small' onClick={handleSearch}>
                  Search
                </Button>
              </Box>
            )}

            {/* Search / Prediction Results */}
            {predictions.length > 0 && showChangeInput && (
              <Box sx={{ mb: 3 }}>
                <Typography variant='subtitle2' color='text.secondary' gutterBottom>
                  Search Results
                </Typography>
                <List dense disablePadding>
                  {predictions.map((pred) => (
                    <ListItem key={pred.soc} disablePadding>
                      <ListItemButton
                        selected={isCurrentPrediction(pred)}
                        onClick={() =>
                          handleSelectSoc(pred.soc, pred.title, pred.score)
                        }
                        sx={{ borderRadius: 1, mb: 0.5 }}
                      >
                        <ListItemText
                          primary={`${pred.soc} \u2014 ${pred.title}`}
                          secondary={`Confidence: ${Math.round(pred.score)}%`}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            {/* Adjacent SOCs */}
            <Box>
              <Typography variant='subtitle2' color='text.secondary' gutterBottom>
                Adjacent Job Classifications
              </Typography>
              {adjacentSocs.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  {adjacentSocs.map((adj) => (
                    <Chip
                      key={adj.soc}
                      label={`${adj.soc} \u2014 ${adj.title}${adj.score ? ` (${Math.round(adj.score)}%)` : ''}`}
                      variant='outlined'
                      onClick={() =>
                        handleSelectSoc(adj.soc, adj.title, adj.score)
                      }
                      sx={{
                        justifyContent: 'flex-start',
                        height: 'auto',
                        py: 1,
                        px: 1,
                        '& .MuiChip-label': { whiteSpace: 'normal' },
                        cursor: 'pointer',
                        '&:hover': { backgroundColor: 'action.hover' }
                      }}
                    />
                  ))}
                </Box>
              ) : (
                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{ fontStyle: 'italic' }}
                >
                  No adjacent classifications found.
                </Typography>
              )}
            </Box>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
