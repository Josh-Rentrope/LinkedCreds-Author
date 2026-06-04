'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
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
  const [skillMatches, setSkillMatches] = useState<{
    hard: string[]
    soft: string[]
  } | null>(null)

  const socCacheRef = useRef<Map<string, SocPrediction>>(new Map())
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const addToCache = useCallback((entries: { soc: string; title: string; score: number }[]) => {
    for (const entry of entries) {
      if (entry.soc && entry.title) {
        socCacheRef.current.set(entry.soc, entry)
      }
    }
  }, [])

  const fuzzyFilterSocs = useCallback(
    (query: string, cache: Map<string, SocPrediction>): SocPrediction[] => {
      if (!query.trim()) return []
      const q = query.toLowerCase().trim()
      const results: SocPrediction[] = []

      for (const entry of cache.values()) {
        const codeMatch = entry.soc.toLowerCase().includes(q)
        const titleMatch = entry.title.toLowerCase().includes(q)
        if (codeMatch || titleMatch) {
          let matchScore = 0
          const socLower = entry.soc.toLowerCase()
          const titleLower = entry.title.toLowerCase()
          if (socLower === q) matchScore = 100
          else if (socLower.startsWith(q)) matchScore = 80
          else if (codeMatch) matchScore = 60
          else if (titleLower === q) matchScore = 90
          else if (titleLower.startsWith(q)) matchScore = 70
          else if (titleMatch) matchScore = 50

          results.push({ ...entry, score: matchScore / 100 })
        }
      }

      results.sort((a, b) => b.score - a.score)
      return results.slice(0, 10)
    },
    []
  )

  // Reset internal state and load data when modal opens or socCode/skills change
  useEffect(() => {
    if (!open) return

    setShowChangeInput(false)
    setSearchQuery('')
    setError(null)
    setPredictions([])
    setSkillMatches(null)

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

        // Populate cache
        addToCache(adjResult.same_category)
        addToCache(adjResult.cross_category)
        if (detailResult) {
          addToCache([{ soc: detailResult.soc, title: detailResult.title, score: 0 }])
          // Compute skill matches from user skills against SOC skills
          const userSkillsLower = skills.map((s) => s.toLowerCase())
          setSkillMatches({
            hard: detailResult.hard_skills.filter((s) =>
              userSkillsLower.includes(s.toLowerCase())
            ),
            soft: detailResult.soft_skills.filter((s) =>
              userSkillsLower.includes(s.toLowerCase())
            ),
          })
        }
      } else if (skills.length > 0) {
        // Auto-detect mode — predict SOC from skills
        const predResult = await predictSocApi(skills, 5, 0.6)
        setPredictions(predResult.predictions)
        addToCache(predResult.predictions)

        if (predResult.predictions.length > 0) {
          const top = predResult.predictions[0]
          setCurrentTitle(top.title)
          setCurrentScore(top.score)
          setSkillMatches({
            hard: top.hard_matches || [],
            soft: top.soft_matches || [],
          })

          // Also fetch adjacent SOCs for top prediction
          const adjResult = await adjacentSocsApi(top.soc, 5, skills)
          setAdjacentSocs(adjResult.same_category)
          addToCache(adjResult.same_category)
          addToCache(adjResult.cross_category)
        } else {
          setCurrentTitle(null)
          setCurrentScore(null)
          setAdjacentSocs([])
          setSkillMatches(null)
        }
      } else {
        // No skills, no selection
        setCurrentTitle(null)
        setCurrentScore(null)
        setAdjacentSocs([])
        setSkillMatches(null)
      }
    } catch (err) {
      console.warn('[SocCodeModal] Failed to load SOC data:', err)
      setError('Failed to load SOC data. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [socCode, skills, addToCache])

  const handleSelectSoc = useCallback(
    async (code: string, title: string, score?: number) => {
      // Commit the selection to parent immediately
      setCurrentTitle(title)
      setCurrentScore(score ?? null)
      setShowChangeInput(false)
      onSocCodeChange(code)

      // Cache this SOC
      addToCache([{ soc: code, title, score: score ?? 0 }])

      // Fetch adjacent SOCs + skill matches for newly selected code
      setLoading(true)
      try {
        const [adjResult, details] = await Promise.all([
          adjacentSocsApi(
            code,
            5,
            skills.length > 0 ? skills : undefined
          ),
          getSocDetailsApi(code),
        ])
        setAdjacentSocs(adjResult.same_category)
        addToCache(adjResult.same_category)
        addToCache(adjResult.cross_category)

        if (details) {
          const userSkillsLower = skills.map((s) => s.toLowerCase())
          setSkillMatches({
            hard: details.hard_skills.filter((s) =>
              userSkillsLower.includes(s.toLowerCase())
            ),
            soft: details.soft_skills.filter((s) =>
              userSkillsLower.includes(s.toLowerCase())
            ),
          })
        }
      } catch (err) {
        console.warn('[SocCodeModal] Failed to fetch adjacent SOCs:', err)
      } finally {
        setLoading(false)
      }
    },
    [skills, onSocCodeChange, addToCache]
  )

  const handleReset = useCallback(() => {
    onSocCodeChange(null)
    setShowChangeInput(false)
  }, [onSocCodeChange])

  const runSearch = useCallback(
    async (query: string) => {
      const q = query.trim()
      if (!q) return

      setLoading(true)
      try {
        const result = await predictSocApi([q], 5, 0.6)
        addToCache(result.predictions)

        // Merge API results with fuzzy cache matches
        const fuzzyResults = fuzzyFilterSocs(q, socCacheRef.current)
        const apiSocs = new Set(result.predictions.map((p) => p.soc))
        const merged = [...result.predictions]

        for (const fuzzy of fuzzyResults) {
          if (!apiSocs.has(fuzzy.soc)) {
            merged.push(fuzzy)
          }
        }

        setPredictions(merged)
      } catch (err) {
        console.warn('[SocCodeModal] Search failed:', err)
        // Fall back to fuzzy cache results
        const fuzzyResults = fuzzyFilterSocs(q, socCacheRef.current)
        if (fuzzyResults.length > 0) {
          setPredictions(fuzzyResults)
        }
      } finally {
        setLoading(false)
      }
    },
    [addToCache, fuzzyFilterSocs]
  )

  const handleSearchInput = useCallback(
    (value: string) => {
      setSearchQuery(value)

      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }

      if (!value.trim()) return

      debounceRef.current = setTimeout(() => {
        runSearch(value)
      }, 300)
    },
    [runSearch]
  )

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

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
                    onClick={
                      !socCode && predictions.length > 0
                        ? () => handleSelectSoc(predictions[0].soc, predictions[0].title, predictions[0].score)
                        : undefined
                    }
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      py: 2.5,
                      px: 1,
                      ...(!socCode && predictions.length > 0 ? { cursor: 'pointer', '&:hover': { boxShadow: 2 } } : {}),
                    }}
                  />
                  {currentScore != null && !isNaN(currentScore) && (
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
                  onChange={(e) => handleSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (debounceRef.current) clearTimeout(debounceRef.current)
                      runSearch(searchQuery)
                    }
                  }}
                />
                <Button
                  variant='contained'
                  size='small'
                  onClick={() => runSearch(searchQuery)}
                >
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
                          secondary={
                            pred.score != null && !isNaN(pred.score)
                              ? `Confidence: ${Math.round(pred.score)}%`
                              : undefined
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            {/* Skill Matches */}
            {(socCode || predictions.length > 0) && (
              <Box sx={{ mb: 2 }}>
                <Typography variant='subtitle2' color='text.secondary' gutterBottom>
                  Skill Matches
                </Typography>
                {skillMatches &&
                (skillMatches.hard.length > 0 || skillMatches.soft.length > 0) ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {skillMatches.hard.length > 0 && (
                      <Box>
                        <Typography
                          variant='caption'
                          color='text.secondary'
                          sx={{ mb: 0.5, display: 'block' }}
                        >
                          Hard Skills
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {skillMatches.hard.map((skill) => (
                            <Chip
                              key={skill}
                              label={skill}
                              size='small'
                              color='success'
                              variant='outlined'
                            />
                          ))}
                        </Box>
                      </Box>
                    )}
                    {skillMatches.soft.length > 0 && (
                      <Box>
                        <Typography
                          variant='caption'
                          color='text.secondary'
                          sx={{ mb: 0.5, display: 'block' }}
                        >
                          Soft Skills
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {skillMatches.soft.map((skill) => (
                            <Chip
                              key={skill}
                              label={skill}
                              size='small'
                              color='info'
                              variant='outlined'
                            />
                          ))}
                        </Box>
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Typography
                    variant='body2'
                    color='text.secondary'
                    sx={{ fontStyle: 'italic' }}
                  >
                    No skill matches found for this classification.
                  </Typography>
                )}
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
